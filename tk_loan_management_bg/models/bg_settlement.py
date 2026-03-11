# -*- coding: utf-8 -*-
"""
Phase 6: Bulgarian Settlement reference model.

Provides a fully-indexed database of 5,256 Bulgarian settlements sourced
from the official NSI EKATTE register, enriched with postcodes and
coordinates from the bgplaces dataset.

Used to populate res.partner address fields via settlement_id Many2one:
  selecting a settlement auto-fills city, zip, state_id, country_id.
"""
from odoo import api, fields, models


class BgSettlement(models.Model):
    """Bulgarian settlement / Населено място (ЕКАТТЕ)"""

    _name        = 'bg.settlement'
    _description = 'Bulgarian Settlement / Населено място'
    _order       = 'name_bg'

    # ── Identifiers ──────────────────────────────────────────────────────────

    ekatte = fields.Char(
        string="ЕКАТТЕ",
        size=5,
        index=True,
        help="Official 5-digit NSI EKATTE code (Единен класификатор на административно-"
             "териториалните и териториалните единици)",
    )

    # ── Names ─────────────────────────────────────────────────────────────────

    name_bg = fields.Char(
        string="Населено място (БГ)",
        required=True,
        index=True,
    )
    name_en = fields.Char(
        string="Settlement (EN)",
        index=True,
    )
    type_prefix = fields.Char(
        string="Вид",
        size=8,
        help="NSI settlement type prefix: с. (село), гр. (град), ман. (манастир) …",
    )
    display_name_bg = fields.Char(
        string="Пълно наименование",
        compute='_compute_display_name_bg',
        store=True,
        index=True,
    )

    @api.depends('type_prefix', 'name_bg')
    def _compute_display_name_bg(self):
        for rec in self:
            prefix = (rec.type_prefix or '').strip()
            name   = (rec.name_bg or '').strip()
            rec.display_name_bg = f"{prefix} {name}".strip() if prefix else name

    # ── Administrative hierarchy ──────────────────────────────────────────────

    obl_code = fields.Char(
        string="Код обл.",
        size=3,
        index=True,
        help="3-letter EKATTE oblast code (BLG, BGS, VAR …)",
    )
    state_id = fields.Many2one(
        comodel_name='res.country.state',
        string="Област",
        index=True,
        ondelete='set null',
    )
    mun_code = fields.Char(
        string="Код общ.",
        size=6,
        help="5-char EKATTE municipality code (BLG52, SML31 …)",
    )
    mun_name = fields.Char(
        string="Община",
    )
    nuts3 = fields.Char(
        string="NUTS3",
        size=6,
        help="Eurostat NUTS-3 code (BG413, BG331 …)",
    )

    # ── Postal / geographic ───────────────────────────────────────────────────

    postcode = fields.Char(
        string="Пощенски код",
        size=10,
    )
    lat = fields.Float(
        string="Latitude",
        digits=(10, 6),
        help="Decimal degrees, WGS-84",
    )
    lng = fields.Float(
        string="Longitude",
        digits=(10, 6),
        help="Decimal degrees, WGS-84",
    )

    # ── Search ────────────────────────────────────────────────────────────────

    _rec_name         = 'display_name_bg'
    _rec_names_search = ['display_name_bg', 'name_bg', 'name_en', 'ekatte', 'postcode']
