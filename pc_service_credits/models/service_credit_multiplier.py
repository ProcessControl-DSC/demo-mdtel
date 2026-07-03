# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class ServiceCreditMultiplier(models.Model):
    _name = 'service.credit.multiplier'
    _description = 'Service Credit Multiplier'

    name = fields.Char(compute='_compute_name', store=True)
    bracket = fields.Selection([
        ('normal', 'Normal'),
        ('after_hours', 'After hours'),
        ('night', 'Night'),
        ('weekend', 'Weekend'),
        ('holiday', 'Holiday'),
    ], required=True)
    factor = fields.Float(required=True, default=1.0)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('bracket', 'factor')
    def _compute_name(self):
        for record in self:
            bracket_label = dict(self._fields['bracket'].selection).get(record.bracket, record.bracket)
            record.name = f"{bracket_label} x{record.factor}"
