# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from datetime import timedelta

from odoo import api, fields, models


class ServiceCreditWallet(models.Model):
    _name = 'service.credit.wallet'
    _inherit = ['mail.thread']
    _description = 'Service Credit Wallet'

    name = fields.Char(compute='_compute_name', store=True)
    partner_id = fields.Many2one('res.partner', required=True, index=True, ondelete='cascade')
    scope = fields.Selection([
        ('general', 'General (customer)'),
        ('analytic', 'Analytic account'),
        ('project', 'Project'),
    ], default='general', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account')
    project_id = fields.Many2one('project.project')
    credit_basis = fields.Selection([
        ('abstract', 'Abstract'),
        ('money', 'Money-equivalent'),
    ], default='abstract', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    move_ids = fields.One2many('service.credit.move', 'wallet_id')
    balance = fields.Float(compute='_compute_balance', store=True)
    move_count = fields.Integer(compute='_compute_move_count')
    low_threshold = fields.Float()
    burn_rate = fields.Float(compute='_compute_burn', help='Consumo medio de créditos por día')
    runout_date = fields.Date(compute='_compute_burn', help='Fecha estimada de agotamiento')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('move_ids.credit_amount', 'move_ids.move_type', 'move_ids.date', 'balance')
    def _compute_burn(self):
        today = fields.Date.context_today(self)
        for w in self:
            cons = w.move_ids.filtered(lambda m: m.move_type == 'consumption')
            total = -sum(cons.mapped('credit_amount'))
            if cons and total > 0:
                first = min(cons.mapped('date'))
                days = max((today - first).days, 1)
                w.burn_rate = total / days
            else:
                w.burn_rate = 0.0
            if w.burn_rate > 0 and w.balance > 0:
                w.runout_date = today + timedelta(days=w.balance / w.burn_rate)
            else:
                w.runout_date = False

    @api.depends('partner_id', 'scope', 'analytic_account_id', 'project_id')
    def _compute_name(self):
        for wallet in self:
            partner_name = wallet.partner_id.name or ''
            if wallet.scope == 'general':
                wallet.name = partner_name
            elif wallet.scope == 'analytic' and wallet.analytic_account_id:
                wallet.name = f"{partner_name} / {wallet.analytic_account_id.name}"
            elif wallet.scope == 'project' and wallet.project_id:
                wallet.name = f"{partner_name} / {wallet.project_id.name}"
            else:
                wallet.name = partner_name

    @api.depends('move_ids.credit_amount')
    def _compute_balance(self):
        for wallet in self:
            wallet.balance = sum(move.credit_amount for move in wallet.move_ids)

    def _compute_move_count(self):
        for wallet in self:
            wallet.move_count = len(wallet.move_ids)

    def _service_credit_notify_shortage(self, line, credits):
        self.ensure_one()
        self.message_post(body=(
            "Saldo insuficiente para el consumo de %.2f créditos (línea %s). "
            "Saldo actual: %.2f." % (credits, line.name or '', self.balance)))

    def _service_credit_expire_fifo(self, today):
        self.ensure_one()
        Move = self.env['service.credit.move']
        topups = self.move_ids.filtered(lambda m: m.move_type == 'topup').sorted(lambda m: (m.lot_date or m.date, m.id))
        remaining = {m.id: m.credit_amount for m in topups}
        total_out = sum(-m.credit_amount for m in self.move_ids if m.credit_amount < 0)
        for m in topups:
            take = min(remaining[m.id], total_out)
            remaining[m.id] -= take
            total_out -= take
            if total_out <= 0:
                break
        for m in topups:
            if m.expiry_date and m.expiry_date < today and remaining[m.id] > 1e-9:
                Move.create({
                    'wallet_id': self.id,
                    'move_type': 'expiry',
                    'credit_amount': -remaining[m.id],
                    'date': today,
                    'lot_date': m.lot_date,
                    'description': 'Credit expiry',
                })

    @api.model
    def _cron_expire_service_credits(self):
        today = fields.Date.context_today(self)
        for wallet in self.search([]):
            wallet._service_credit_expire_fifo(today)
