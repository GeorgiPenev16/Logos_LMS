# -*- coding: utf-8 -*-
{
    'name': 'Loan Management - Bulgarian Localization',
    'summary': 'Bulgarian compliance additions for Customer Loan Management',
    'description': """
        Добавки за българско законодателство към модул за управление на кредити.

        Включва:
        - Поддръжка на фирмени кредитополучатели (ЕИК, МОЛ, БУЛСТАТ)
        - Роля „Поръчител" свързана с кредита
        - Изчисление на ГПР по метода XIRR (ЗПК, чл. 19)
        - Динамичен шаблон за договор (редактируем от администратора)
        - Редактируема таблица на вноски
        - Полета за AnaCredit отчетност към БНБ
    """,
    'version': '1.0.12',
    'author': 'VitoshaBG EOOD',
    'company': 'VitoshaBG EOOD',
    'maintainer': 'VitoshaBG EOOD',
    'website': 'https://vitoshabg.eu',
    'category': 'Accounting/Localizations',
    'license': 'LGPL-3',

    'depends': [
        'tk_loan_management',
    ],

    'data': [
        # Security
        'security/ir.model.access.csv',

        # Phase 6: Bulgarian address reference data
        # Load order matters: oblasts → settlements (settlements reference state records)
        'data/res_country_state_bg.xml',   # 28 oblasts → res.country.state (noupdate=1)
        'data/bg.settlement.csv',          # 5,256 settlements → bg.settlement

        # GROUP A: Chart of accounts and journals (noupdate=1, before views)
        'data/account_chart_bg.xml',
        'data/account_journals_bg.xml',

        # Views — Фаза 2
        'views/partner_bg_views.xml',
        'views/loan_bg_views.xml',

        # Views — Фаза 4
        'views/loan_gpr_views.xml',

        # Views — Phase 6: Bulgarian address
        'views/bg_settlement_views.xml',

        # GROUP A: Settings view
        'views/res_config_settings_bg_views.xml',

        # Views — Фаза 5: Document System
        'views/document_template_views.xml',

        # Reports — Фаза 5
        'reports/loan_document_report.xml',

        # Default data — Фаза 5 (noupdate=1)
        'data/document_templates_data.xml',
    ],

    'assets': {},

    'installable': True,
    'auto_install': False,
    'application': False,
}
