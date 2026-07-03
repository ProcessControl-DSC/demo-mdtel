# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    service_credit_enabled = fields.Boolean(
        related='company_id.service_credit_enabled', readonly=False)
    service_credit_default_rate = fields.Float(
        related='company_id.service_credit_default_rate', readonly=False)
    service_credit_time_mode = fields.Selection(
        related='company_id.service_credit_time_mode', readonly=False)
    service_credit_night_start = fields.Float(
        related='company_id.service_credit_night_start', readonly=False)
    service_credit_night_end = fields.Float(
        related='company_id.service_credit_night_end', readonly=False)
    service_credit_fallback_policy = fields.Selection(
        related='company_id.service_credit_fallback_policy', readonly=False)
    service_credit_shortage_policy = fields.Selection(
        related='company_id.service_credit_shortage_policy', readonly=False)
    service_credit_overdraft_limit = fields.Float(
        related='company_id.service_credit_overdraft_limit', readonly=False)
    service_credit_deferred_enabled = fields.Boolean(
        related='company_id.service_credit_deferred_enabled', readonly=False)
    service_credit_deferred_journal_id = fields.Many2one(
        related='company_id.service_credit_deferred_journal_id', readonly=False)
    service_credit_deferred_account_id = fields.Many2one(
        related='company_id.service_credit_deferred_account_id', readonly=False)
    service_credit_income_account_id = fields.Many2one(
        related='company_id.service_credit_income_account_id', readonly=False)
    service_credit_value_per_credit = fields.Float(
        related='company_id.service_credit_value_per_credit', readonly=False)
