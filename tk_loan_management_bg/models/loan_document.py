# -*- coding: utf-8 -*-
"""
Phase 5 — Loan Generated Document model and Generate wizard.

Workflow:
  1. User clicks "Generate Document" on the loan form (Documents tab).
  2. Wizard opens → user selects a loan.document.template.
  3. action_generate() renders the template:
       - Substitutes all {placeholder} tokens with live loan data.
       - Saves rendered HTML as loan.generated.document record.
       - Generates PDF via QWeb → saved as ir.attachment on the loan.
       - Generates DOCX via python-docx (if available) → saved as ir.attachment.
  4. Generated files appear in the "Generated Documents" list on the loan form.
"""
import base64
import logging
from datetime import date

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

try:
    from docx import Document as DocxDocument
    from docx.shared import Pt, Cm
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Bulgarian number-to-words helpers
# ─────────────────────────────────────────────────────────────────────────────

_BG_ONES = [
    '', 'един', 'два', 'три', 'четири', 'пет', 'шест', 'седем', 'осем', 'девет',
    'десет', 'единадесет', 'дванадесет', 'тринадесет', 'четиринадесет',
    'петнадесет', 'шестнадесет', 'седемнадесет', 'осемнадесет', 'деветнадесет',
]
_BG_TENS = [
    '', 'десет', 'двадесет', 'тридесет', 'четиридесет', 'петдесет',
    'шестдесет', 'седемдесет', 'осемдесет', 'деветдесет',
]


def _bg_below_1000(n):
    """Convert integer 1..999 to Bulgarian words."""
    if n == 0:
        return ''
    parts = []
    hundreds = n // 100
    remainder = n % 100
    if hundreds == 1:
        parts.append('сто')
    elif hundreds == 2:
        parts.append('двеста')
    elif hundreds == 3:
        parts.append('триста')
    elif hundreds >= 4:
        parts.append(_BG_ONES[hundreds] + 'ста' if hundreds <= 6 else _BG_ONES[hundreds] + 'стотин')
        # correct forms
        _map = {4: 'четиристотин', 5: 'петстотин', 6: 'шестотин',
                7: 'седемстотин', 8: 'осемстотин', 9: 'деветстотин'}
        parts[-1] = _map[hundreds]
    if remainder < 20:
        if remainder:
            parts.append(_BG_ONES[remainder])
    else:
        tens = remainder // 10
        ones = remainder % 10
        parts.append(_BG_TENS[tens])
        if ones:
            parts.append(_BG_ONES[ones])
    return ' '.join(p for p in parts if p)


def _number_to_bg_words(amount):
    """
    Convert a monetary amount (float) to Bulgarian words.
    Returns e.g. "хиляда и двеста лева и 00 стотинки"
    """
    amount = round(float(amount), 2)
    integer_part = int(amount)
    cents = round((amount - integer_part) * 100)

    if integer_part == 0:
        lv_words = 'нула'
    elif integer_part < 0:
        lv_words = 'минус ' + _number_to_bg_words_integer(-integer_part)
    else:
        lv_words = _number_to_bg_words_integer(integer_part)

    return f"{lv_words} лева и {cents:02d} стотинки"


def _number_to_bg_words_integer(n):
    """Convert positive integer to Bulgarian words."""
    if n == 0:
        return 'нула'
    parts = []
    millions = n // 1_000_000
    thousands = (n % 1_000_000) // 1_000
    below_thousand = n % 1_000

    if millions:
        m_word = _bg_below_1000(millions)
        if millions == 1:
            parts.append('един милион')
        else:
            parts.append(m_word + ' милиона')

    if thousands:
        if thousands == 1:
            parts.append('хиляда')
        elif thousands == 2:
            parts.append('две хиляди')
        else:
            t_word = _bg_below_1000(thousands)
            parts.append(t_word + ' хиляди')

    if below_thousand:
        b_word = _bg_below_1000(below_thousand)
        if parts:
            parts.append('и ' + b_word)
        else:
            parts.append(b_word)

    return ' '.join(parts)


def _bg_date(d):
    """Format a date as Bulgarian long-form string: 10 март 2026 г."""
    if not d:
        return ''
    _months = [
        '', 'януари', 'февруари', 'март', 'април', 'май', 'юни',
        'юли', 'август', 'септември', 'октомври', 'ноември', 'декември',
    ]
    return f"{d.day} {_months[d.month]} {d.year} г."


# ─────────────────────────────────────────────────────────────────────────────
# Generated Document model
# ─────────────────────────────────────────────────────────────────────────────

class LoanGeneratedDocument(models.Model):
    """Генериран документ към кредит."""

    _name = 'loan.generated.document'
    _description = 'Generated Loan Document / Генериран документ'
    _order = 'generated_date desc'

    loan_id = fields.Many2one(
        comodel_name='customer.loan',
        string="Loan / Кредит",
        required=True,
        ondelete='cascade',
    )
    template_id = fields.Many2one(
        comodel_name='loan.document.template',
        string="Template / Шаблон",
        required=True,
        ondelete='restrict',
    )
    name = fields.Char(
        string="Document Name / Наименование",
        compute='_compute_name',
        store=True,
    )
    generated_date = fields.Datetime(
        string="Generated On / Генериран на",
        default=fields.Datetime.now,
        readonly=True,
    )
    content_rendered = fields.Html(
        string="Rendered Content / Съдържание",
        readonly=True,
        sanitize=False,
    )
    state = fields.Selection(
        selection=[
            ('draft',     'Чернова'),
            ('generated', 'Генериран'),
            ('signed',    'Подписан'),
        ],
        string="Status / Статус",
        default='draft',
    )
    attachment_pdf_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="PDF",
        readonly=True,
    )
    attachment_docx_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="DOCX",
        readonly=True,
    )

    @api.depends('template_id', 'loan_id')
    def _compute_name(self):
        for rec in self:
            t = rec.template_id.name if rec.template_id else ''
            l = rec.loan_id.name if rec.loan_id else ''
            rec.name = f"{t} — {l}" if t and l else (t or l or _("New Document"))

    # ── Placeholder rendering ─────────────────────────────────────────────────

    def _build_placeholder_map(self):
        """Return dict of {placeholder: value} for the loan."""
        self.ensure_one()
        loan = self.loan_id
        company = loan.company_id or self.env.company

        # Borrower
        borrower = loan.customer_id
        b_name    = borrower.name or ''
        b_egn     = (borrower.personal_number or '') if not borrower.is_company else ''
        b_eik     = (borrower.company_registry or '') if borrower.is_company else ''
        b_parts   = [p for p in [borrower.street, borrower.city] if p]
        b_address = ', '.join(b_parts)

        # Represented by (МОЛ of borrower company)
        rep    = loan.represented_by if hasattr(loan, 'represented_by') else False
        rep_name = rep.name if rep else ''
        rep_egn  = (rep.personal_number if rep and hasattr(rep, 'personal_number') else '') or ''

        # Guarantors
        g_lines = loan.guarantor_line_ids if hasattr(loan, 'guarantor_line_ids') else []
        g1 = g_lines[0].partner_id if g_lines else False
        g1_name = g1.name if g1 else ''
        g1_egn  = (g1.personal_number if g1 and hasattr(g1, 'personal_number') else '') or ''

        # Co-debtors
        c_lines = loan.codebtor_line_ids if hasattr(loan, 'codebtor_line_ids') else []
        c1 = c_lines[0].partner_id if c_lines else False
        c1_name = c1.name if c1 else ''
        c1_egn  = (c1.personal_number if c1 and hasattr(c1, 'personal_number') else '') or ''

        # Lending company
        co_mol_parts = []
        if hasattr(company, 'manager_id') and company.manager_id:
            co_mol_parts = [company.manager_id.name or '']
        co_mol = co_mol_parts[0] if co_mol_parts else ''

        # Financial fields (may be absent if Phase 4 not installed)
        gpr_val     = getattr(loan, 'gpr', 0.0) or 0.0
        total_pay   = getattr(loan, 'total_amount_payable', 0.0) or 0.0
        total_cost  = getattr(loan, 'total_cost_of_credit', 0.0) or 0.0

        # Format currency
        currency_symbol = loan.currency_id.symbol if loan.currency_id else 'лв.'

        def fmt_money(v):
            return f"{v:,.2f} {currency_symbol}"

        # Instalment amount
        instalment = loan.installment_amount or 0.0

        return {
            # Loan
            'loan_ref':          loan.name or '',
            'loan_date':         _bg_date(loan.app_date),
            'loan_amount':       fmt_money(loan.loan_amount or 0),
            'loan_amount_words': _number_to_bg_words(loan.loan_amount or 0),
            'interest_rate':     f"{loan.interest_rate or 0:.2f}",
            'gpr':               f"{gpr_val:.6f}",
            'term':              str(loan.term or ''),
            'monthly_payment':   fmt_money(instalment),
            'total_payable':     fmt_money(total_pay),
            'total_cost':        fmt_money(total_cost),
            'start_date':        _bg_date(loan.installment_start_date),
            # Borrower
            'borrower_name':     b_name,
            'borrower_egn':      b_egn,
            'borrower_eik':      b_eik,
            'borrower_address':  b_address,
            'represented_by':    rep_name,
            'represented_egn':   rep_egn,
            # Guarantors / co-debtors
            'guarantor_1_name':  g1_name,
            'guarantor_1_egn':   g1_egn,
            'codebtor_1_name':   c1_name,
            'codebtor_1_egn':    c1_egn,
            # Company
            'company_name':      company.name or '',
            'company_eik':       company.company_registry or '',
            'company_address':   company.street or '',
            'company_mol':       co_mol,
            'city':              company.city or '',
            # Date
            'today_date':        _bg_date(date.today()),
        }

    def _render_content(self):
        """Substitute all {placeholder} tokens in template content."""
        self.ensure_one()
        content = self.template_id.content or ''
        mapping = self._build_placeholder_map()
        for key, value in mapping.items():
            content = content.replace('{' + key + '}', str(value))
        return content

    # ── Document generation ───────────────────────────────────────────────────

    def action_generate(self):
        """Render template, generate PDF and DOCX, save as ir.attachment."""
        self.ensure_one()
        rendered = self._render_content()
        self.content_rendered = rendered

        loan = self.loan_id
        doc_name = self.name

        # ── PDF via QWeb ──────────────────────────────────────────────────────
        try:
            report = self.env.ref(
                'tk_loan_management_bg.loan_document_report_action',
                raise_if_not_found=False,
            )
            if report:
                pdf_content, _ = report._render_qweb_pdf([self.id])
                pdf_attachment = self.env['ir.attachment'].create({
                    'name':      doc_name + '.pdf',
                    'type':      'binary',
                    'datas':     base64.b64encode(pdf_content),
                    'res_model': 'customer.loan',
                    'res_id':    loan.id,
                    'mimetype':  'application/pdf',
                })
                self.attachment_pdf_id = pdf_attachment
        except Exception as e:
            _logger.warning("PDF generation failed for loan.generated.document %s: %s", self.id, e)

        # ── DOCX via python-docx ──────────────────────────────────────────────
        if _DOCX_AVAILABLE:
            try:
                docx_bytes = self._generate_docx(rendered, doc_name)
                docx_attachment = self.env['ir.attachment'].create({
                    'name':      doc_name + '.docx',
                    'type':      'binary',
                    'datas':     base64.b64encode(docx_bytes),
                    'res_model': 'customer.loan',
                    'res_id':    loan.id,
                    'mimetype':  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                })
                self.attachment_docx_id = docx_attachment
            except Exception as e:
                _logger.warning("DOCX generation failed for loan.generated.document %s: %s", self.id, e)

        self.state = 'generated'
        return True

    def _generate_docx(self, html_content, title):
        """Convert rendered HTML to a simple DOCX file. Returns bytes."""
        import io
        import re

        doc = DocxDocument()

        # Page margins — A4
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        section = doc.sections[0]
        section.page_width  = Cm(21)
        section.page_height = Cm(29.7)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.0)
        section.top_margin    = Cm(2.5)
        section.bottom_margin = Cm(2.0)

        # Strip HTML tags to plain text, preserving paragraph breaks
        # Replace block-level tags with newlines
        text = re.sub(r'<br\s*/?>', '\n', html_content, flags=re.IGNORECASE)
        text = re.sub(r'</(p|div|h[1-6]|li|tr)>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')

        # Title paragraph
        title_para = doc.add_paragraph(title)
        title_para.style = doc.styles['Heading 1']

        # Split into paragraphs and add
        paragraphs = [p.strip() for p in text.split('\n')]
        for para_text in paragraphs:
            if para_text:
                p = doc.add_paragraph(para_text)
                p.style.font.size = Pt(11)

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Generate Wizard
# ─────────────────────────────────────────────────────────────────────────────

class LoanDocumentGenerateWizard(models.TransientModel):
    """Wizard: select template → generate document for a loan."""

    _name = 'loan.document.generate.wizard'
    _description = 'Generate Loan Document Wizard / Генериране на документ'

    loan_id = fields.Many2one(
        comodel_name='customer.loan',
        string="Loan / Кредит",
        required=True,
        readonly=True,
    )
    template_id = fields.Many2one(
        comodel_name='loan.document.template',
        string="Template / Шаблон",
        required=True,
        domain="[('is_active', '=', True)]",
    )

    def action_generate(self):
        """Generate the document and return the generated record view."""
        self.ensure_one()
        gen_doc = self.env['loan.generated.document'].create({
            'loan_id':     self.loan_id.id,
            'template_id': self.template_id.id,
            'state':       'draft',
        })
        gen_doc.action_generate()

        # Return to the loan form
        return {
            'type':    'ir.actions.act_window',
            'res_model': 'customer.loan',
            'res_id':    self.loan_id.id,
            'view_mode': 'form',
            'target':    'main',
        }
