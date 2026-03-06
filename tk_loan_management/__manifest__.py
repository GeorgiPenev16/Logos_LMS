# -*- coding: utf-8 -*-
# Copyright 2024 - Today Techkhedut.

# Part of Techkhedut. See LICENSE file for full copyright and licensing details.

{
    'name': 'Customer Loan Management',
    'description': """
        - Customer Loan Management
    """,
    'summary': """
        Customer Loan Management
    """,
    'version': '1.0.8',
    'author': 'TechKhedut Inc.',
    'company': 'TechKhedut Inc.',
    'maintainer': 'TechKhedut Inc.',
    'website': "https://www.techkhedut.com",
    'depends': [
        'base',
        'crm',
        'contacts',
        'stock',
        'sale_management',
        'account',
        'portal',
        'website',
        'accountant'
    ],
    'data': [
        # Data
        'data/sequence_data.xml',
        'data/ir_cron.xml',
        # Mail templates
        'data/sanction_letter_mail.xml',
        'data/customer_signed_loan_mail.xml',
        'data/loan_disbursement_confirmation_mail.xml',
        'data/installment_reminder_mail.xml',
        'data/installment_overdue_penalty_mail.xml',
        'data/document_request_mail.xml',
        'data/collateral_request_mail.xml',
        'data/loan_request_submitted_mail.xml',
        'data/loan_request_approved_mail.xml',
        'data/revised_instalment_schedule_mail.xml',
        # Security
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        # Wizard
        'wizard/customer_loan_reject_reason_wizard_views.xml',
        'wizard/customer_loan_cancel_reason_wizard_views.xml',
        'wizard/customer_document_reject_reason_wizard_views.xml',
        'wizard/customer_pre_closure_wizard_views.xml',
        'wizard/customer_loan_settlement_wizard_views.xml',
        'wizard/request_document_from_customer_wizard_views.xml',
        'wizard/request_collateral_from_customer_wizard_views.xml',
        'wizard/loan_payment_view.xml',
        # Inherited Views
        'views/customer_loan_account_move_views.xml',
        'views/customer_loan_crm_lead_inherit_view.xml',
        # Views
        'views/assets.xml',
        'views/customer_loan_views.xml',
        'views/customer_loan_type_views.xml',
        'views/customer_installments_term_templates_views.xml',
        'views/customer_terms_and_conditions_template_views.xml',
        'views/customer_repayment_terms_template_views.xml',
        'views/customer_document_type_views.xml',
        'views/customer_collateral_type_views.xml',
        'views/customer_loan_res_config_settings_views.xml',
        'views/res_partner.xml',
        'views/family_info_view.xml',
        'views/labour_relation_view.xml',
        'views/public_holidays_views.xml',
        # Web templates
        'views/templates/customer_portal_template.xml',
        'views/templates/lead_website_template.xml',
        'views/templates/upload_document_template.xml',
        'views/templates/upload_collateral_template.xml',
        # Reports
        'reports/sanction_letter_report.xml',
        'reports/closure_letter_report.xml',
        'reports/noc_letter_report.xml',
        'reports/settlement_letter_report.xml',
        'reports/signature_certificate_report.xml',
        'reports/loan_contract.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'tk_loan_management/static/src/js/script.js',
            'tk_loan_management/static/src/css/style.css',
        ],

        'web.assets_backend': [
            'tk_loan_management/static/src/xml/template.xml',
            'tk_loan_management/static/src/scss/style.scss',
            'tk_loan_management/static/src/js/lib/apexcharts.js',
            'tk_loan_management/static/src/js/lib/xy.js',
            'tk_loan_management/static/src/js/lib/index.js',
            'tk_loan_management/static/src/js/lib/percent.js',
            'tk_loan_management/static/src/js/lib/Animated.js',
            'tk_loan_management/static/src/js/dashboard/customer_loan_dashboard.js',
        ],

    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
}
