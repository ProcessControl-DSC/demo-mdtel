# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from dateutil.relativedelta import relativedelta

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            order._service_credit_generate_topups()
        return res

    def _service_credit_generate_topups(self):
        self.ensure_one()
        company = self.company_id
        if not company.service_credit_enabled:
            return
        Move = self.env['service.credit.move']
        for line in self.order_line:
            prod = line.product_id.product_tmpl_id
            if not prod.is_service_credit_bono or not prod.service_credit_granted:
                continue
            existing = Move.search([
                ('sale_line_id', '=', line.id),
                ('move_type', '=', 'topup'),
            ], limit=1)
            if existing:
                continue
            wallet = line.credit_wallet_id or company._service_credit_general_wallet(self.partner_id)
            credits = line.product_uom_qty * prod.service_credit_granted
            today = fields.Date.context_today(self)
            vals = {
                'wallet_id': wallet.id,
                'move_type': 'topup',
                'credit_amount': credits,
                'sale_line_id': line.id,
                'date': today,
                'lot_date': today,
                'description': prod.name,
            }
            if prod.service_credit_validity_months:
                vals['expiry_date'] = today + relativedelta(months=prod.service_credit_validity_months)
            Move.create(vals)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    credit_wallet_id = fields.Many2one('service.credit.wallet', string="Service credit wallet (top-up target)")
