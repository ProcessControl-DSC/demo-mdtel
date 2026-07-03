# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_service_credit_bono = fields.Boolean(default=False)
    service_credit_granted = fields.Float()
    service_credit_validity_months = fields.Integer(default=0)
