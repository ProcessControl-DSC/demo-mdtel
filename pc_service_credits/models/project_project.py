# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    credit_wallet_target_id = fields.Many2one('service.credit.wallet', string="Service credit wallet")
