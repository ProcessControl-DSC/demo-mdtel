# Copyright 2026 Process Control
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class ServiceCreditPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'credit_count' in counters:
            partner = request.env.user.partner_id.commercial_partner_id
            values['credit_count'] = request.env['service.credit.wallet'].sudo().search_count(
                [('partner_id', '=', partner.id)])
        return values

    @http.route(['/my/service_credits'], type='http', auth='user', website=True)
    def portal_my_service_credits(self, **kw):
        partner = request.env.user.partner_id.commercial_partner_id
        wallets = request.env['service.credit.wallet'].sudo().search([('partner_id', '=', partner.id)])
        return request.render('pc_service_credits.portal_my_service_credits', {
            'wallets': wallets, 'page_name': 'service_credits'})

    @http.route(['/my/service_credits/<int:wallet_id>'], type='http', auth='user', website=True)
    def portal_service_credit_detail(self, wallet_id, **kw):
        partner = request.env.user.partner_id.commercial_partner_id
        wallet = request.env['service.credit.wallet'].sudo().browse(wallet_id)
        if not wallet.exists() or wallet.partner_id != partner:
            return request.redirect('/my')
        return request.render('pc_service_credits.portal_service_credit_detail', {
            'wallet': wallet, 'moves': wallet.move_ids, 'page_name': 'service_credit'})
