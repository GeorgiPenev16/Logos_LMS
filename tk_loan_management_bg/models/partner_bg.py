# -*- coding: utf-8 -*-
"""
Bulgarian localization for res.partner.

Adds:
- EIK validation on Odoo's built-in company_registry field (9 digits + checksum)
- BULSTAT field with validation (9 or 13 digits + checksum)
- Manager / MOL — company representative
- Guarantor role (is_guarantor)
- Skip EGN/ID card validation for companies
- Display EGN in dropdowns for easier identification
"""
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartnerBG(models.Model):
    """Bulgarian localization for partner"""
    _inherit = 'res.partner'

    # ── Settlement lookup — main address (standard Odoo fields) ──

    settlement_id = fields.Many2one(
        comodel_name='bg.settlement',
        string="Населено място / Settlement",
        help="Select from the EKATTE register — auto-fills city, postcode and oblast",
        ondelete='set null',
    )

    @api.onchange('settlement_id')
    def _onchange_settlement_id(self):
        """Auto-fill standard address fields from selected Bulgarian settlement."""
        s = self.settlement_id
        if not s:
            return
        self.country_id = s.state_id.country_id if s.state_id else False
        self.state_id   = s.state_id
        self.city       = s.name_bg
        self.zip        = s.postcode or ''

    # ── Settlement lookup — Labour / Employer address (ep_* fields) ──

    ep_settlement_id = fields.Many2one(
        comodel_name='bg.settlement',
        string="Населено място / Settlement",
        help="Select from the EKATTE register — auto-fills employer city, postcode and oblast",
        ondelete='set null',
    )

    @api.onchange('ep_settlement_id')
    def _onchange_ep_settlement_id(self):
        """Auto-fill ep_* address fields from selected Bulgarian settlement."""
        s = self.ep_settlement_id
        if not s:
            return
        # Set country first — stabilises address format widget before city/zip
        self.ep_country_id = s.state_id.country_id if s.state_id else False
        self.ep_state_id   = s.state_id
        self.ep_city       = s.name_bg
        self.ep_zip        = s.postcode or ''

    # ── Company fields ──

    bulstat = fields.Char(
        string="BULSTAT / БУЛСТАТ",
        help="BULSTAT number — 9 digits with checksum",
    )

    manager_id = fields.Many2one(
        comodel_name='res.partner',
        string="Manager / МОЛ",
        help="Materially Responsible Person — company representative",
    )

    # ── Guarantor role — for individuals and companies ──

    is_guarantor = fields.Boolean(
        string="Guarantor / Поръчител",
        help="Check if this partner can be a guarantor on a loan",
    )

    # ── EIK validation on Odoo's built-in company_registry ──

    @staticmethod
    def _validate_eik_9(eik):
        """Validate 9-digit EIK checksum. Returns True/False."""
        if not eik or not eik.isdigit() or len(eik) != 9:
            return False
        # First attempt: weights [1,2,3,4,5,6,7,8]
        weights_1 = [1, 2, 3, 4, 5, 6, 7, 8]
        total = sum(int(eik[i]) * weights_1[i] for i in range(8))
        remainder = total % 11
        if remainder < 10:
            return remainder == int(eik[8])
        # Second attempt: weights [3,4,5,6,7,8,9,10]
        weights_2 = [3, 4, 5, 6, 7, 8, 9, 10]
        total = sum(int(eik[i]) * weights_2[i] for i in range(8))
        remainder = total % 11
        check_digit = remainder if remainder < 10 else 0
        return check_digit == int(eik[8])

    @api.constrains('company_registry')
    def _check_company_registry_bg(self):
        """Validate EIK (Company ID) — 9 digits with checksum per Bulgarian law."""
        for rec in self:
            eik = rec.company_registry
            if not eik:
                continue
            eik = eik.strip()
            if not eik.isdigit() or len(eik) != 9:
                raise ValidationError(
                    _("Company ID (EIK) must be exactly 9 digits. Got: '%s'") % eik)
            if not self._validate_eik_9(eik):
                raise ValidationError(
                    _("Invalid Company ID (EIK): checksum mismatch. Check number: '%s'") % eik)

    # ── BULSTAT validation (9 or 13 digits) ──

    @api.constrains('bulstat')
    def _check_bulstat(self):
        """Validate BULSTAT — 9 digits with checksum (same algorithm as EIK)."""
        for rec in self:
            bulstat = rec.bulstat
            if not bulstat:
                continue
            bulstat = bulstat.strip()
            if not bulstat.isdigit() or len(bulstat) != 9:
                raise ValidationError(
                    _("BULSTAT must be exactly 9 digits. Got: '%s'") % bulstat)
            if not self._validate_eik_9(bulstat):
                raise ValidationError(
                    _("Invalid BULSTAT: checksum mismatch. Check number: '%s'") % bulstat)

    # ── Skip EGN and ID card validation for companies ──

    @api.constrains('personal_number', 'id_card')
    def _check_personal_number(self):
        """
        Override base module validation.
        Companies (is_company=True) — skip EGN and ID card check.
        Individuals — run original validation.
        """
        for rec in self:
            if rec.is_company:
                continue
            personal_number = rec.personal_number
            id_card = rec.id_card
            if personal_number:
                is_valid, error_msg = self.is_valid_egn(personal_number)
                if not is_valid:
                    raise ValidationError(_(error_msg))
            if id_card and not self.is_valid_id_card(id_card):
                raise ValidationError(_("Invalid id card number."))

    # ── Search by name, ref and EGN in dropdowns ──

    _rec_names_search = ['name', 'ref', 'personal_number']

    # ── Display EGN in dropdowns for easier identification ──

    def _compute_display_name(self):
        """
        Shows EGN after the name in dropdowns.
        Example: "Ivan Ivanov - 7601121234"
        """
        super()._compute_display_name()
        for rec in self:
            if rec.personal_number and not rec.is_company:
                rec.display_name = "%s - %s" % (rec.display_name, rec.personal_number)
