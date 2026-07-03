# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class ServiceCreditMove(models.Model):
    _name = 'service.credit.move'
    _description = 'Service Credit Move'

    name = fields.Char(default='/')
    wallet_id = fields.Many2one('service.credit.wallet', required=True, index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='wallet_id.partner_id', store=True)
    move_type = fields.Selection([
        ('topup', 'Top-up'),
        ('consumption', 'Consumption'),
        ('adjustment', 'Adjustment'),
        ('reversal', 'Reversal'),
        ('expiry', 'Expiry'),
    ], required=True)
    credit_amount = fields.Float(required=True)
    date = fields.Date(default=fields.Date.context_today, required=True, index=True)
    lot_date = fields.Date()
    description = fields.Char()
    analytic_line_id = fields.Many2one('account.analytic.line', ondelete='set null')
    sale_line_id = fields.Many2one('sale.order.line', ondelete='set null')
    expiry_date = fields.Date()
    reversed_move_id = fields.Many2one('service.credit.move')
    account_move_id = fields.Many2one('account.move')
    origin_employee_id = fields.Many2one('hr.employee', related='analytic_line_id.employee_id', store=True)
    origin_project_id = fields.Many2one('project.project', related='analytic_line_id.project_id', store=True)
    origin_task_id = fields.Many2one('project.task', related='analytic_line_id.task_id', store=True)
    origin_bracket = fields.Selection(related='analytic_line_id.credit_time_bracket', store=True)
    company_id = fields.Many2one('res.company', related='wallet_id.company_id', store=True)

    def _service_credit_recognize(self):
        self.ensure_one()
        if self.move_type != 'consumption' or self.account_move_id:
            return
        company = self.wallet_id.company_id
        if not company.service_credit_deferred_enabled:
            return
        journal = company.service_credit_deferred_journal_id
        deferred = company.service_credit_deferred_account_id
        income = company.service_credit_income_account_id
        if not (journal and deferred and income):
            return
        amount = abs(self.credit_amount) * company.service_credit_value_per_credit
        if amount <= 0:
            return
        am = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': self.date,
            'ref': 'Service credits: %s' % (self.description or self.wallet_id.name or ''),
            'line_ids': [
                (0, 0, {'account_id': deferred.id, 'debit': amount, 'credit': 0.0, 'name': 'Credit recognition'}),
                (0, 0, {'account_id': income.id, 'debit': 0.0, 'credit': amount, 'name': 'Credit recognition'}),
            ],
        })
        am.action_post()
        self.account_move_id = am.id
