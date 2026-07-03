# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    credit_time_bracket = fields.Selection([
        ('normal', 'Normal'),
        ('after_hours', 'After hours'),
        ('night', 'Night'),
        ('weekend', 'Weekend'),
        ('holiday', 'Holiday'),
    ], default='normal')
    credit_datetime = fields.Datetime()
    credit_wallet_id = fields.Many2one('service.credit.wallet', string="Service credit wallet (override)")
    credit_move_ids = fields.One2many('service.credit.move', 'analytic_line_id')

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            line._service_credit_apply()
        return lines

    def write(self, vals):
        res = super().write(vals)
        trigger = {'unit_amount', 'employee_id', 'credit_time_bracket', 'credit_datetime',
                   'credit_wallet_id', 'project_id', 'task_id', 'date'}
        if trigger & set(vals.keys()):
            for line in self:
                line._service_credit_apply()
        return res

    def _service_credit_apply(self):
        # El consumo es un efecto de sistema: se ejecuta en sudo para no exigir
        # permisos de créditos al usuario que imputa horas.
        self.ensure_one()
        company = self.company_id
        if not company or not company.service_credit_enabled:
            return
        line_su = self.sudo()
        line_su.credit_move_ids.unlink()
        if not self.employee_id or not self.unit_amount:
            return
        wallet = line_su._service_credit_resolve_wallet()
        if not wallet:
            raise UserError("No hay bono/monedero disponible para imputar (revise contrato/proyecto o el bono general).")
        bracket = line_su._service_credit_bracket()
        credits = company.sudo().service_credit_convert(self.employee_id, self.unit_amount, bracket)
        projected = wallet.balance - credits
        policy = company.service_credit_shortage_policy
        if projected < 0:
            if policy == 'block':
                raise UserError("Saldo de créditos insuficiente para esta imputación.")
            if policy == 'overdraft' and projected < -company.service_credit_overdraft_limit:
                raise UserError("Se supera el límite de descubierto de créditos.")
            wallet._service_credit_notify_shortage(self, credits)
        move = self.env['service.credit.move'].sudo().create({
            'wallet_id': wallet.id,
            'move_type': 'consumption',
            'credit_amount': -credits,
            'analytic_line_id': self.id,
            'date': self.date or fields.Date.context_today(self),
            'description': self.name,
        })
        move._service_credit_recognize()

    def _service_credit_resolve_wallet(self):
        self.ensure_one()
        # 1) override explícito en la línea
        if self.credit_wallet_id:
            return self.credit_wallet_id
        # 2) tarea
        task = self.task_id
        if task and task.credit_wallet_target_id:
            return task.credit_wallet_target_id
        # 3) proyecto
        project = self.project_id or (task.project_id if task else False)
        if project and project.credit_wallet_target_id:
            return project.credit_wallet_target_id
        # 4) fallback según política de la company
        partner = self.partner_id or (task.partner_id if task else False) or (project.partner_id if project else False)
        policy = self.company_id.service_credit_fallback_policy
        if policy == 'general' and partner:
            return self.company_id._service_credit_general_wallet(partner)
        return self.env['service.credit.wallet']

    def _service_credit_bracket(self):
        self.ensure_one()
        mode = self.company_id.service_credit_time_mode
        if mode == 'auto':
            return self.company_id.service_credit_classify_bracket(
                self.credit_datetime or fields.Datetime.now())
        if mode == 'hybrid':
            if self.credit_datetime:
                return self.company_id.service_credit_classify_bracket(self.credit_datetime)
            return self.credit_time_bracket
        return self.credit_time_bracket
