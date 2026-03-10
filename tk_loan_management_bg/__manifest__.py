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
    'version': '1.0.1',
    'author': 'VitoshaBG EOOD',
    'company': 'VitoshaBG EOOD',
    'maintainer': 'VitoshaBG EOOD',
    'website': 'https://vitoshabg.com',
    'category': 'Accounting/Localizations',
    'license': 'LGPL-3',

    'depends': [
        'tk_loan_management',
    ],

    'data': [
        # Security
        'security/ir.model.access.csv',

        # Views — Фаза 2
        'views/partner_bg_views.xml',
        'views/loan_bg_views.xml',
    ],

    'assets': {},

    'installable': True,
    'auto_install': False,
    'application': False,
}
