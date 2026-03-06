# -*- coding: utf-8 -*-
"""
Разширение на res.partner за българско законодателство.

Добавя:
- ЕИК (9 цифри) за юридически лица с валидация по контролна сума
- БУЛСТАТ (13 цифри) за нетърговски субекти
- МОЛ (Материално Отговорно Лице) — управител на фирмата
- Роля „Поръчител" (is_guarantor)
- Пропускане на ЕГН/лична карта валидация за фирми
- Показване на ЕГН в name_get за по-лесно разпознаване
"""
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartnerBG(models.Model):
    """Българска локализация на партньор"""
    _inherit = 'res.partner'

    # ── Полета за юридически лица (фирми) ──

    company_id_bg = fields.Char(
        string="Company ID / ЕИК",
        help="Единен идентификационен код — 9 цифри с контролна сума",
    )

    bulstat = fields.Char(
        string="BULSTAT / БУЛСТАТ",
        help="БУЛСТАТ за нетърговски субекти — 13 цифри",
    )

    manager_id = fields.Many2one(
        comodel_name='res.partner',
        string="Manager / МОЛ",
        help="Материално Отговорно Лице — управител на фирмата",
        # Domain moved to XML view — 'id' in Python domain causes JS eval
        # errors on unsaved records, which can break the entire group render.
    )

    # ── Guarantor role — for individuals and companies ──

    is_guarantor = fields.Boolean(
        string="Guarantor / Поръчител",
        help="Check if this partner can be a guarantor on a loan",
    )

    # ── Валидация на ЕИК (9 цифри с контролна сума) ──

    @api.constrains('company_id_bg')
    def _check_company_id_bg(self):
        """Валидация на ЕИК — 9 цифри с контролна сума по алгоритъм на НАП."""
        for rec in self:
            eik = rec.company_id_bg
            if not eik:
                continue
            eik = eik.strip()
            if not eik.isdigit() or len(eik) != 9:
                raise ValidationError(
                    _("ЕИК трябва да съдържа точно 9 цифри. Получена стойност: '%s'") % eik)
            # Контролна сума — първи опит с тежести [1,2,3,4,5,6,7,8]
            weights_1 = [1, 2, 3, 4, 5, 6, 7, 8]
            total = sum(int(eik[i]) * weights_1[i] for i in range(8))
            remainder = total % 11
            if remainder < 10:
                check_digit = remainder
            else:
                # Втори опит с тежести [3,4,5,6,7,8,9,10]
                weights_2 = [3, 4, 5, 6, 7, 8, 9, 10]
                total = sum(int(eik[i]) * weights_2[i] for i in range(8))
                remainder = total % 11
                check_digit = remainder if remainder < 10 else 0
            if check_digit != int(eik[8]):
                raise ValidationError(
                    _("Невалиден ЕИК: контролната сума не съвпада. Проверете номера: '%s'") % eik)

    # ── Валидация на БУЛСТАТ (13 цифри) ──

    @api.constrains('bulstat')
    def _check_bulstat(self):
        """Валидация на БУЛСТАТ — 13 цифри с контролна сума."""
        for rec in self:
            bulstat = rec.bulstat
            if not bulstat:
                continue
            bulstat = bulstat.strip()
            if not bulstat.isdigit() or len(bulstat) != 13:
                raise ValidationError(
                    _("БУЛСТАТ трябва да съдържа точно 13 цифри. Получена стойност: '%s'") % bulstat)
            # Първите 9 цифри се валидират като ЕИК
            eik_part = bulstat[:9]
            weights_1 = [1, 2, 3, 4, 5, 6, 7, 8]
            total = sum(int(eik_part[i]) * weights_1[i] for i in range(8))
            remainder = total % 11
            if remainder < 10:
                check_9 = remainder
            else:
                weights_2 = [3, 4, 5, 6, 7, 8, 9, 10]
                total = sum(int(eik_part[i]) * weights_2[i] for i in range(8))
                remainder = total % 11
                check_9 = remainder if remainder < 10 else 0
            if check_9 != int(bulstat[8]):
                raise ValidationError(
                    _("Невалиден БУЛСТАТ: контролната сума на първите 9 цифри не съвпада: '%s'")
                    % bulstat)
            # Контролна сума за 13-та цифра (тежести [2,7,3,5])
            weights_13_1 = [2, 7, 3, 5]
            total = sum(int(bulstat[i + 8]) * weights_13_1[i] for i in range(4))
            remainder = total % 11
            if remainder < 10:
                check_13 = remainder
            else:
                weights_13_2 = [4, 9, 5, 7]
                total = sum(int(bulstat[i + 8]) * weights_13_2[i] for i in range(4))
                remainder = total % 11
                check_13 = remainder if remainder < 10 else 0
            if check_13 != int(bulstat[12]):
                raise ValidationError(
                    _("Невалиден БУЛСТАТ: контролната сума на 13-та цифра не съвпада: '%s'")
                    % bulstat)

    # ── Пропускане на ЕГН и лична карта валидация за фирми ──

    @api.constrains('personal_number', 'id_card')
    def _check_personal_number(self):
        """
        Преопределяне на валидацията от tk_loan_management.
        За фирми (is_company=True) — пропуска проверката на ЕГН и лична карта.
        За физически лица — извиква оригиналната валидация.
        """
        for rec in self:
            # Фирмите нямат ЕГН и лична карта — пропускаме
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

    # ── Показване на ЕГН в name_get за по-лесно разпознаване ──

    def _compute_display_name(self):
        """
        Показва ЕГН след името в падащи менюта.
        Пример: "Иван Иванов - 7601121234"
        Помага при избор на правилния човек когато има еднакви имена.
        """
        super()._compute_display_name()
        for rec in self:
            if rec.personal_number and not rec.is_company:
                rec.display_name = "%s - %s" % (rec.display_name, rec.personal_number)
