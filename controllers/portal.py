# -*- coding: utf-8 -*-

import base64

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request
from odoo.modules.module import get_module_resource

from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager


REQUEST_STATES = {
    'draft': ('Rascunho', 'muted'),
    'submitted': ('Recebida', 'info'),
    'quoted': ('Cotação preparada', 'primary'),
    'confirmed': ('Confirmada', 'success'),
    'preparing': ('Em preparação', 'warning'),
    'dispatched': ('Em transporte', 'info'),
    'delivered': ('Entregue', 'success'),
    'cancelled': ('Cancelada', 'secondary'),
}

APPLICATION_STATES = {
    'submitted': ('Recebida', 'info'),
    'review': ('Em avaliação', 'warning'),
    'shortlisted': ('Pré-seleccionada', 'primary'),
    'accepted': ('Aceite', 'success'),
    'rejected': ('Não seleccionada', 'secondary'),
    'withdrawn': ('Retirada', 'muted'),
}

ALLOWED_ATTACHMENT_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'webp', 'xls', 'xlsx',
}


class GesCustomerPortal(portal.CustomerPortal):

    @http.route('/ges/assets/portal-light.css', type='http', auth='public', website=False, sitemap=False)
    def ges_portal_light_css(self, **kw):
        css_path = get_module_resource('js_website_ges', 'static/src/scss', 'ges_portal_light.css')
        with open(css_path, 'rb') as css_file:
            content = css_file.read()
        return request.make_response(content, headers=[
            ('Content-Type', 'text/css; charset=utf-8'),
            ('Cache-Control', 'public, max-age=604800'),
        ])

    @staticmethod
    def _safe_int(value, default=0, minimum=0, maximum=10000):
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        return min(maximum, max(minimum, parsed))

    @staticmethod
    def _safe_float(value, default=0.0, minimum=0.0, maximum=999999999.0):
        try:
            parsed = float(str(value or '').replace(',', '.'))
        except (TypeError, ValueError):
            parsed = default
        return min(maximum, max(minimum, parsed))

    @staticmethod
    def _safe_filename(filename):
        cleaned = (filename or '').rsplit('/', 1)[-1].rsplit('\\', 1)[-1].strip()
        return cleaned[:180] or 'documento'

    def _attachment_errors(self, uploads):
        errors = []
        for upload in uploads:
            if not upload or not upload.filename:
                continue
            filename = self._safe_filename(upload.filename)
            extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
                errors.append(_('Formato não permitido: %s') % filename)
            if getattr(upload, 'content_length', 0) and upload.content_length > 10 * 1024 * 1024:
                errors.append(_('O ficheiro %s excede 10 MB.') % filename)
        return errors

    def _create_attachments(self, uploads, res_model, res_id):
        attachments = request.env['ir.attachment'].sudo()
        for upload in uploads:
            if not upload or not upload.filename:
                continue
            filename = self._safe_filename(upload.filename)
            payload = upload.read()
            if not payload:
                continue
            attachments |= request.env['ir.attachment'].sudo().create({
                'name': filename,
                'datas': base64.b64encode(payload),
                'res_model': res_model,
                'res_id': res_id,
                'mimetype': upload.mimetype,
            })
        return attachments

    def _profile_document_values(self, profile):
        if not profile:
            return {'documents': request.env['ir.attachment'], 'certificates': request.env['ir.attachment']}
        return {
            'documents': profile.document_attachment_ids,
            'certificates': profile.certification_attachment_ids,
        }

    def _subcontractor_profile(self):
        if request.env.user._is_public():
            return request.env['ges.subcontractor.profile']
        partner = request.env.user.partner_id.commercial_partner_id
        return request.env['ges.subcontractor.profile'].sudo().search([
            ('partner_id', 'child_of', partner.id),
        ], limit=1)

    def _published_jobs_domain(self):
        return [
            ('state', '=', 'published'),
            '|', ('deadline', '=', False), ('deadline', '>=', fields.Date.today()),
        ]

    def _ges_request_domain(self):
        partner = request.env.user.partner_id.commercial_partner_id
        return [('partner_id', 'child_of', partner.id)]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'ges_request_count' in counters:
            values['ges_request_count'] = request.env['ges.material.request'].search_count(
                self._ges_request_domain()
            )
        return values

    def _ges_products(self):
        return request.env['product.product'].sudo().search([
            ('active', '=', True),
            ('sale_ok', '=', True),
            ('product_tmpl_id.ges_portal_available', '=', True),
        ], order='categ_id, name')

    def _ges_product_prices(self, products):
        pricelist = request.env.user.partner_id.property_product_pricelist
        return {
            product.id: product.with_context(pricelist=pricelist.id).price
            for product in products
        }

    def _ges_layout_values(self):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        request_model = request.env['ges.material.request']
        domain = self._ges_request_domain()
        values.update({
            'partner': partner,
            'ges_request_count': request_model.search_count(domain),
            'ges_open_count': request_model.search_count(domain + [('state', 'not in', ['delivered', 'cancelled'])]),
            'ges_delivered_count': request_model.search_count(domain + [('state', '=', 'delivered')]),
            'ges_states': REQUEST_STATES,
        })
        return values

    @http.route(['/my/ges'], type='http', auth='user', website=True)
    def ges_portal_dashboard(self, **kw):
        values = self._ges_layout_values()
        values.update({
            'page_name': 'ges_dashboard',
            'requests': request.env['ges.material.request'].search(
                self._ges_request_domain(), order='create_date desc', limit=5,
            ),
            'quotation_count': request.env['sale.order'].search_count(self._prepare_quotations_domain(values['partner'])),
            'order_count': request.env['sale.order'].search_count(self._prepare_orders_domain(values['partner'])),
        })
        return request.render('js_website_ges.ges_portal_dashboard', values)

    @http.route(['/my/ges/requests', '/my/ges/requests/page/<int:page>'], type='http', auth='user', website=True)
    def ges_portal_requests(self, page=1, sortby='newest', state='all', **kw):
        values = self._ges_layout_values()
        domain = self._ges_request_domain()
        sortings = {
            'newest': {'label': _('Mais recentes'), 'order': 'create_date desc'},
            'oldest': {'label': _('Mais antigas'), 'order': 'create_date asc'},
            'reference': {'label': _('Referência'), 'order': 'name desc'},
        }
        if sortby not in sortings:
            sortby = 'newest'
        if state in REQUEST_STATES:
            domain.append(('state', '=', state))
        else:
            state = 'all'
        total = request.env['ges.material.request'].search_count(domain)
        pager = portal_pager(
            url='/my/ges/requests',
            url_args={'sortby': sortby, 'state': state},
            total=total,
            page=page,
            step=20,
        )
        requests = request.env['ges.material.request'].search(
            domain, order=sortings[sortby]['order'], limit=20, offset=pager['offset'],
        )
        request.session['my_ges_requests_history'] = requests.ids[:100]
        values.update({
            'page_name': 'ges_requests',
            'requests': requests,
            'pager': pager,
            'sortby': sortby,
            'state_filter': state,
            'searchbar_sortings': sortings,
        })
        return request.render('js_website_ges.ges_portal_requests', values)

    @http.route('/my/ges/calculator', type='http', auth='user', website=True)
    def ges_portal_calculator(self, **kw):
        values = self._ges_layout_values()
        values.update({
            'page_name': 'ges_calculator',
            'products': self._ges_products(),
            'today': fields.Date.today(),
            'error': kw.get('error'),
            'form_values': {},
        })
        values['product_prices'] = self._ges_product_prices(values['products'])
        return request.render('js_website_ges.ges_portal_calculator', values)

    @http.route('/my/ges/requests/create', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def ges_portal_request_create(self, **post):
        products = self._ges_products()
        product_by_id = {product.id: product for product in products}
        errors = []
        project_name = (post.get('project_name') or '').strip()
        site_location = (post.get('site_location') or '').strip()
        if not project_name:
            errors.append(_('Indique o nome do projecto ou obra.'))
        if not site_location:
            errors.append(_('Indique o local de entrega.'))

        required_date = False
        if post.get('required_date'):
            try:
                required_date = fields.Date.from_string(post['required_date'])
            except (TypeError, ValueError):
                errors.append(_('A data necessária não é válida.'))

        line_values = []
        for key, raw_value in post.items():
            if not key.startswith('qty_'):
                continue
            try:
                product_id = int(key[4:])
                quantity = float((raw_value or '0').replace(',', '.'))
            except (TypeError, ValueError):
                continue
            product = product_by_id.get(product_id)
            if not product or quantity <= 0:
                continue
            quantity = min(quantity, 100000000.0)
            price = product.with_context(pricelist=request.env.user.partner_id.property_product_pricelist.id).price
            line_values.append((0, 0, {
                'product_id': product.id,
                'name': product.get_product_multiline_description_sale() or product.display_name,
                'quantity': quantity,
                'uom_id': product.uom_id.id,
                'price_unit_estimated': price,
            }))
        if not line_values:
            errors.append(_('Adicione pelo menos um material com quantidade superior a zero.'))

        if errors:
            values = self._ges_layout_values()
            values.update({
                'page_name': 'ges_calculator',
                'products': products,
                'product_prices': self._ges_product_prices(products),
                'today': fields.Date.today(),
                'errors': errors,
                'form_values': post,
            })
            return request.render('js_website_ges.ges_portal_calculator', values)

        partner = request.env.user.partner_id.commercial_partner_id
        material_request = request.env['ges.material.request'].sudo().create({
            'partner_id': partner.id,
            'user_id': partner.user_id.id or False,
            'project_name': project_name,
            'site_location': site_location,
            'required_date': required_date,
            'notes': (post.get('notes') or '').strip(),
            'line_ids': line_values,
        })
        try:
            material_request.action_submit()
        except (UserError, ValidationError) as error:
            material_request.unlink()
            values = self._ges_layout_values()
            values.update({
                'page_name': 'ges_calculator',
                'products': products,
                'product_prices': self._ges_product_prices(products),
                'today': fields.Date.today(),
                'errors': [str(error)],
                'form_values': post,
            })
            return request.render('js_website_ges.ges_portal_calculator', values)
        return request.redirect('/my/ges/requests/%s?created=1' % material_request.id)

    @http.route('/my/ges/requests/<int:request_id>', type='http', auth='user', website=True)
    def ges_portal_request_detail(self, request_id, access_token=None, **kw):
        try:
            material_request = self._document_check_access(
                'ges.material.request', request_id, access_token=access_token,
            )
        except (AccessError, MissingError):
            return request.redirect('/my/ges/requests')
        values = self._ges_layout_values()
        values.update({
            'page_name': 'ges_request_detail',
            'material_request': material_request,
            'created': kw.get('created') == '1',
        })
        return request.render('js_website_ges.ges_portal_request_detail', values)

    @http.route(['/subempreiteiros', '/subempreiteiros/vagas'], type='http', auth='public', website=True)
    def ges_subcontractor_public(self, **kw):
        jobs = request.env['ges.subcontractor.job'].sudo().search(self._published_jobs_domain(), limit=30)
        return request.render('js_website_ges.ges_subcontractor_public', {
            'page_name': 'ges_subcontractor_public',
            'jobs': jobs,
            'registered': kw.get('registered') == '1',
        })

    @http.route('/subempreiteiros/cadastro', type='http', auth='public', website=True, methods=['GET', 'POST'], csrf=True)
    def ges_subcontractor_register(self, **post):
        if not request.env.user._is_public():
            return request.redirect('/my/ges/subempreiteiro/perfil')
        errors = []
        if request.httprequest.method == 'POST':
            document_uploads = request.httprequest.files.getlist('documents')
            certificate_uploads = request.httprequest.files.getlist('certificates')
            name = (post.get('name') or '').strip()
            email = (post.get('email') or '').strip().lower()
            phone = (post.get('phone') or '').strip()
            company_name = (post.get('company_name') or '').strip()
            trades = (post.get('trades') or '').strip()
            if not all([name, email, phone, company_name, trades]):
                errors.append(_('Preencha todos os campos obrigatórios.'))
            if '@' not in email or len(email) > 254:
                errors.append(_('Indique um endereço de email válido.'))
            errors.extend(self._attachment_errors(document_uploads))
            errors.extend(self._attachment_errors(certificate_uploads))
            existing = request.env['res.partner'].sudo().search([('email', '=ilike', email)], limit=1)
            if existing:
                errors.append(_('Este email já está registado. Entre na sua conta para criar ou actualizar o perfil.'))
            if not errors:
                partner = request.env['res.partner'].sudo().create({
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'company_type': 'person',
                })
                request.env['ges.subcontractor.profile'].sudo().create({
                    'partner_id': partner.id,
                    'company_name': company_name,
                    'legal_name': (post.get('legal_name') or company_name).strip(),
                    'nuit': (post.get('nuit') or '').strip(),
                    'phone': phone,
                    'email': email,
                    'supplier_type': post.get('supplier_type') or 'company',
                    'street': (post.get('street') or '').strip(),
                    'city': (post.get('city') or '').strip(),
                    'province': (post.get('province') or '').strip(),
                    'coverage_area': (post.get('coverage_area') or '').strip(),
                    'trades': trades,
                    'team_size': self._safe_int(post.get('team_size'), default=1, minimum=1),
                    'years_experience': self._safe_int(post.get('years_experience'), maximum=100),
                    'availability': post.get('availability') or 'scheduled',
                    'service_pricing': (post.get('service_pricing') or '').strip(),
                    'price_range_min': self._safe_float(post.get('price_range_min')),
                    'price_range_max': self._safe_float(post.get('price_range_max')),
                    'presentation': (post.get('presentation') or '').strip(),
                })
                profile = request.env['ges.subcontractor.profile'].sudo().search([
                    ('partner_id', '=', partner.id),
                ], limit=1)
                documents = self._create_attachments(document_uploads, 'ges.subcontractor.profile', profile.id)
                certificates = self._create_attachments(certificate_uploads, 'ges.subcontractor.profile', profile.id)
                if documents:
                    profile.sudo().write({'document_attachment_ids': [(4, attachment.id) for attachment in documents]})
                if certificates:
                    profile.sudo().write({'certification_attachment_ids': [(4, attachment.id) for attachment in certificates]})
                partner.signup_prepare()
                signup_url = partner.with_context(relative_url=True)._get_signup_url_for_action(
                    url='/my/ges/subempreiteiro',
                )[partner.id]
                return request.redirect(signup_url)
        return request.render('js_website_ges.ges_subcontractor_register', {
            'page_name': 'ges_subcontractor_register',
            'errors': errors,
            'form_values': post,
        })

    @http.route('/my/ges/subempreiteiro', type='http', auth='user', website=True)
    def ges_subcontractor_dashboard(self, **kw):
        profile = self._subcontractor_profile()
        applications = request.env['ges.subcontractor.application'].sudo().search([
            ('profile_id', '=', profile.id),
        ], limit=20) if profile else request.env['ges.subcontractor.application']
        jobs = request.env['ges.subcontractor.job'].sudo().search(self._published_jobs_domain(), limit=12)
        return request.render('js_website_ges.ges_subcontractor_dashboard', {
            'page_name': 'ges_subcontractor_dashboard',
            'profile': profile,
            'applications': applications,
            'jobs': jobs,
            'application_states': APPLICATION_STATES,
            'profile_documents': self._profile_document_values(profile),
            'saved': kw.get('saved') == '1',
        })

    @http.route('/my/ges/subempreiteiro/perfil', type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=True)
    def ges_subcontractor_profile(self, **post):
        profile = self._subcontractor_profile()
        errors = []
        if request.httprequest.method == 'POST':
            document_uploads = request.httprequest.files.getlist('documents')
            certificate_uploads = request.httprequest.files.getlist('certificates')
            company_name = (post.get('company_name') or '').strip()
            phone = (post.get('phone') or '').strip()
            trades = (post.get('trades') or '').strip()
            if not all([company_name, phone, trades]):
                errors.append(_('Preencha empresa, telefone e especialidades.'))
            errors.extend(self._attachment_errors(document_uploads))
            errors.extend(self._attachment_errors(certificate_uploads))
            if not errors:
                values = {
                    'partner_id': request.env.user.partner_id.commercial_partner_id.id,
                    'company_name': company_name,
                    'legal_name': (post.get('legal_name') or company_name).strip(),
                    'nuit': (post.get('nuit') or '').strip(),
                    'phone': phone,
                    'email': request.env.user.partner_id.email or request.env.user.login,
                    'supplier_type': post.get('supplier_type') or 'company',
                    'tax_regime': (post.get('tax_regime') or '').strip(),
                    'license_number': (post.get('license_number') or '').strip(),
                    'street': (post.get('street') or '').strip(),
                    'city': (post.get('city') or '').strip(),
                    'province': (post.get('province') or '').strip(),
                    'coverage_area': (post.get('coverage_area') or '').strip(),
                    'trades': trades,
                    'service_pricing': (post.get('service_pricing') or '').strip(),
                    'price_range_min': self._safe_float(post.get('price_range_min')),
                    'price_range_max': self._safe_float(post.get('price_range_max')),
                    'team_size': self._safe_int(post.get('team_size'), default=1, minimum=1),
                    'years_experience': self._safe_int(post.get('years_experience'), maximum=100),
                    'availability': post.get('availability') or 'scheduled',
                    'equipment': (post.get('equipment') or '').strip(),
                    'certifications': (post.get('certifications') or '').strip(),
                    'presentation': (post.get('presentation') or '').strip(),
                    'bank_name': (post.get('bank_name') or '').strip(),
                    'bank_account': (post.get('bank_account') or '').strip(),
                    'payment_terms': (post.get('payment_terms') or '').strip(),
                }
                if profile:
                    profile.sudo().write(values)
                else:
                    profile = request.env['ges.subcontractor.profile'].sudo().create(values)
                documents = self._create_attachments(document_uploads, 'ges.subcontractor.profile', profile.id)
                certificates = self._create_attachments(certificate_uploads, 'ges.subcontractor.profile', profile.id)
                if documents:
                    profile.sudo().write({'document_attachment_ids': [(4, attachment.id) for attachment in documents]})
                if certificates:
                    profile.sudo().write({'certification_attachment_ids': [(4, attachment.id) for attachment in certificates]})
                return request.redirect('/my/ges/subempreiteiro?saved=1')
        return request.render('js_website_ges.ges_subcontractor_profile', {
            'page_name': 'ges_subcontractor_profile',
            'profile': profile,
            'errors': errors,
            'form_values': post,
            'profile_documents': self._profile_document_values(profile),
        })

    @http.route('/my/ges/subempreiteiro/vagas/<int:job_id>', type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=True)
    def ges_subcontractor_job(self, job_id, **post):
        job = request.env['ges.subcontractor.job'].sudo().search(
            [('id', '=', job_id)] + self._published_jobs_domain(), limit=1,
        )
        if not job:
            return request.redirect('/my/ges/subempreiteiro')
        profile = self._subcontractor_profile()
        if not profile:
            return request.redirect('/my/ges/subempreiteiro/perfil')
        application = request.env['ges.subcontractor.application'].sudo().search([
            ('job_id', '=', job.id), ('profile_id', '=', profile.id),
        ], limit=1)
        errors = []
        if request.httprequest.method == 'POST' and not application:
            application_uploads = request.httprequest.files.getlist('application_documents')
            message = (post.get('message') or '').strip()
            if len(message) < 30:
                errors.append(_('Explique a sua experiência e proposta em pelo menos 30 caracteres.'))
            errors.extend(self._attachment_errors(application_uploads))
            if not errors:
                application = request.env['ges.subcontractor.application'].sudo().create({
                    'job_id': job.id,
                    'profile_id': profile.id,
                    'message': message,
                    'availability_date': post.get('availability_date') or False,
                    'proposed_team_size': self._safe_int(post.get('proposed_team_size'), default=profile.team_size or 1, minimum=1),
                    'proposed_price': self._safe_float(post.get('proposed_price')),
                    'execution_days': self._safe_int(post.get('execution_days'), maximum=3650),
                })
                attachments = self._create_attachments(application_uploads, 'ges.subcontractor.application', application.id)
                if attachments:
                    application.sudo().write({'attachment_ids': [(4, attachment.id) for attachment in attachments]})
                return request.redirect('/my/ges/subempreiteiro?applied=1')
        return request.render('js_website_ges.ges_subcontractor_job', {
            'page_name': 'ges_subcontractor_job',
            'job': job,
            'profile': profile,
            'application': application,
            'application_states': APPLICATION_STATES,
            'errors': errors,
            'form_values': post,
        })

    @http.route('/my/ges/subempreiteiro/documentos/<int:attachment_id>', type='http', auth='user', website=True)
    def ges_subcontractor_document_download(self, attachment_id, **kw):
        profile = self._subcontractor_profile()
        if not profile:
            return request.not_found()
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id).exists()
        allowed_profile_docs = profile.document_attachment_ids | profile.certification_attachment_ids
        allowed_application_docs = profile.application_ids.mapped('attachment_ids')
        if not attachment or attachment not in (allowed_profile_docs | allowed_application_docs):
            return request.not_found()
        status, headers, content = request.env['ir.http'].sudo().binary_content(
            id=attachment.id, download=True, filename=attachment.name,
        )
        if status != 200:
            return request.not_found()
        return request.make_response(content, headers)
