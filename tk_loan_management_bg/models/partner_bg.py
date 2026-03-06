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

    # ── Company fields ──

    bulstat = fields.Char(
        string="BULSTAT / БУЛСТАТ",
        help="BULSTAT number — 9 or 13 digits with checksum",
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
        """Validate BULSTAT — 9 or 13 digits with checksum."""
        for rec in self:
            bulstat = rec.bulstat
            if not bulstat:
                continue
            bulstat = bulstat.strip()
            if not bulstat.isdigit() or len(bulstat) not in (9, 13):
                raise ValidationError(
                    _("BULSTAT must be 9 or 13 digits. Got: '%s'") % bulstat)
            # First 9 digits — same checksum as EIK
            if not self._validate_eik_9(bulstat[:9]):
                raise ValidationError(
                    _("Invalid BULSTAT: first 9 digits checksum mismatch: '%s'") % bulstat)
            # 13-digit BULSTAT — additional checksum for 13th digit
            if len(bulstat) == 13:
                # Weights [2,7,3,5] on digits at positions 8,9,10,11
                weights_1 = [2, 7, 3, 5]
                total = sum(int(bulstat[i + 8]) * weights_1[i] for i in range(4))
                remainder = total % 11
                if remainder < 10:
                    check_13 = remainder
                else:
                    # Fallback weights [4,9,5,7]
                    weights_2 = [4, 9, 5, 7]
                    total = sum(int(bulstat[i + 8]) * weights_2[i] for i in range(4))
                    remainder = total % 11
                    check_13 = remainder if remainder < 10 else 0
                if check_13 != int(bulstat[12]):
                    raise ValidationError(
                        _("Invalid BULSTAT: 13th digit checksum mismatch: '%s'") % bulstat)

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
