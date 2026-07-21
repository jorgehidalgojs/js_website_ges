# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ges_portal_available = fields.Boolean(
        string='Disponível no Portal GES',
        help='Permite que clientes adicionem este produto às suas requisições no portal.',
    )
    ges_calculator_type = fields.Selection([
        ('manual', 'Quantidade manual'),
        ('concrete', 'Volume de betão'),
        ('blocks', 'Blocos para parede'),
        ('area', 'Área com desperdício'),
    ], string='Calculadora GES', default='manual', required=True)
    ges_portal_description = fields.Char(
        string='Descrição curta no portal',
        translate=True,
    )


class GesMaterialRequest(models.Model):
    _name = 'ges.material.request'
    _description = 'Requisição de Material GES'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Referência', default='Novo', copy=False, readonly=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, index=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Responsável comercial', tracking=True)
    project_name = fields.Char(string='Projecto / obra', required=True, tracking=True)
    site_location = fields.Char(string='Local de entrega', required=True, tracking=True)
    required_date = fields.Date(string='Data necessária', tracking=True)
    notes = fields.Text(string='Observações')
    state = fields.Selection([
        ('draft', 'Rascunho'),
        ('submitted', 'Recebida'),
        ('quoted', 'Cotação preparada'),
        ('confirmed', 'Confirmada'),
        ('preparing', 'Em preparação'),
        ('dispatched', 'Em transporte'),
        ('delivered', 'Entregue'),
        ('cancelled', 'Cancelada'),
    ], string='Estado', default='draft', required=True, tracking=True, index=True)
    line_ids = fields.One2many('ges.material.request.line', 'request_id', string='Materiais', copy=True)
    sale_order_id = fields.Many2one('sale.order', string='Cotação / pedido', copy=False, readonly=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', store=True, readonly=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Empresa', default=lambda self: self.env.company, required=True,
    )
    amount_estimated = fields.Monetary(
        string='Estimativa', compute='_compute_amount_estimated', store=True,
    )
    item_count = fields.Integer(string='Itens', compute='_compute_item_count')

    @api.depends('line_ids.subtotal_estimated')
    def _compute_amount_estimated(self):
        for request in self:
            request.amount_estimated = sum(request.line_ids.mapped('subtotal_estimated'))

    @api.depends('line_ids')
    def _compute_item_count(self):
        for request in self:
            request.item_count = len(request.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Novo') == 'Novo':
                vals['name'] = self.env['ir.sequence'].next_by_code('ges.material.request') or 'Novo'
        return super().create(vals_list)

    def _prepare_sale_order_vals(self):
        self.ensure_one()
        lines = []
        for line in self.line_ids:
            taxes = line.product_id.taxes_id.filtered(lambda tax: tax.company_id == self.company_id)
            lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name or line.product_id.get_product_multiline_description_sale(),
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'price_unit': line.price_unit_estimated,
                'tax_id': [(6, 0, taxes.ids)],
            }))
        return {
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id.id or self.partner_id.user_id.id or False,
            'origin': self.name,
            'client_order_ref': self.project_name,
            'note': _('Estimativa criada a partir da requisição %s no Portal GES. Valores sujeitos a validação comercial.\nLocal: %s\nData necessária: %s\n\n%s') % (
                self.name,
                self.site_location,
                self.required_date or '-',
                self.notes or '',
            ),
            'ges_request_id': self.id,
            'order_line': lines,
        }

    def action_submit(self):
        for request in self:
            if not request.line_ids:
                raise UserError(_('Adicione pelo menos um material à requisição.'))
            if not request.sale_order_id:
                order = self.env['sale.order'].create(request._prepare_sale_order_vals())
                order.write({'state': 'sent'})
                request.sale_order_id = order
            request.state = 'quoted'
            request.message_post(body=_('Requisição recebida pelo Portal GES e cotação %s criada.') % request.sale_order_id.name)
        return True

    def action_set_submitted(self):
        self.write({'state': 'submitted'})

    def action_set_preparing(self):
        self.write({'state': 'preparing'})

    def action_set_dispatched(self):
        self.write({'state': 'dispatched'})

    def action_set_delivered(self):
        self.write({'state': 'delivered'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cotação'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
        }

    def _compute_access_url(self):
        super()._compute_access_url()
        for request in self:
            request.access_url = '/my/ges/requests/%s' % request.id


class GesMaterialRequestLine(models.Model):
    _name = 'ges.material.request.line'
    _description = 'Linha de Requisição de Material GES'
    _order = 'id'

    request_id = fields.Many2one('ges.material.request', string='Requisição', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Material / serviço', required=True)
    name = fields.Char(string='Descrição', required=True)
    quantity = fields.Float(string='Quantidade', required=True, default=1.0, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='Unidade', required=True)
    price_unit_estimated = fields.Float(string='Preço unitário estimado', digits='Product Price')
    currency_id = fields.Many2one(related='request_id.currency_id', readonly=True)
    subtotal_estimated = fields.Monetary(string='Subtotal estimado', compute='_compute_subtotal', store=True)

    @api.depends('quantity', 'price_unit_estimated')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal_estimated = line.quantity * line.price_unit_estimated


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ges_request_id = fields.Many2one('ges.material.request', string='Requisição Portal GES', copy=False, index=True)

    def action_confirm(self):
        result = super().action_confirm()
        self.filtered('ges_request_id').mapped('ges_request_id').write({'state': 'confirmed'})
        return result

    def action_cancel(self):
        result = super().action_cancel()
        self.filtered('ges_request_id').mapped('ges_request_id').write({'state': 'cancelled'})
        return result


class GesSubcontractorProfile(models.Model):
    _name = 'ges.subcontractor.profile'
    _description = 'Perfil de Subempreiteiro GES'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'company_name'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='Contacto', required=True, ondelete='cascade', index=True, tracking=True)
    company_name = fields.Char(string='Empresa / equipa', required=True, tracking=True)
    legal_name = fields.Char(string='Razão social')
    nuit = fields.Char(string='NUIT', tracking=True)
    phone = fields.Char(string='Telefone', required=True)
    email = fields.Char(string='Email', required=True, index=True)
    supplier_type = fields.Selection([
        ('company', 'Empresa formal'),
        ('team', 'Equipa técnica'),
        ('individual', 'Técnico independente'),
    ], string='Tipo de fornecedor', default='company', required=True)
    tax_regime = fields.Char(string='Regime fiscal')
    license_number = fields.Char(string='Licença / alvará')
    street = fields.Char(string='Endereço')
    city = fields.Char(string='Cidade / distrito')
    province = fields.Char(string='Província')
    coverage_area = fields.Char(string='Área de cobertura')
    trades = fields.Char(string='Especialidades', required=True, help='Ex.: construção civil, electricidade, canalização.')
    service_pricing = fields.Text(string='Serviços e preços')
    price_range_min = fields.Monetary(string='Preço mínimo indicativo')
    price_range_max = fields.Monetary(string='Preço máximo indicativo')
    currency_id = fields.Many2one('res.currency', string='Moeda', default=lambda self: self.env.company.currency_id)
    team_size = fields.Integer(string='Tamanho da equipa', default=1)
    years_experience = fields.Integer(string='Anos de experiência')
    availability = fields.Selection([
        ('immediate', 'Disponível imediatamente'),
        ('scheduled', 'Disponível por agenda'),
        ('limited', 'Capacidade limitada'),
    ], string='Disponibilidade', default='scheduled')
    equipment = fields.Text(string='Equipamentos disponíveis')
    certifications = fields.Text(string='Licenças e certificações')
    presentation = fields.Text(string='Apresentação / experiência')
    bank_name = fields.Char(string='Banco')
    bank_account = fields.Char(string='Conta bancária')
    payment_terms = fields.Char(string='Condições de pagamento')
    document_attachment_ids = fields.Many2many(
        'ir.attachment', 'ges_subcontractor_profile_document_rel',
        'profile_id', 'attachment_id', string='Documentos do fornecedor',
        help='NUIT, alvará, certidão, documentos legais e carta de apresentação.',
    )
    certification_attachment_ids = fields.Many2many(
        'ir.attachment', 'ges_subcontractor_profile_certificate_rel',
        'profile_id', 'attachment_id', string='Certificados anexados',
    )
    state = fields.Selection([
        ('pending', 'Em análise'),
        ('approved', 'Aprovado'),
        ('suspended', 'Suspenso'),
    ], string='Estado', default='pending', required=True, tracking=True, index=True)
    application_ids = fields.One2many('ges.subcontractor.application', 'profile_id', string='Candidaturas')
    application_count = fields.Integer(compute='_compute_application_count', string='Candidaturas')
    document_count = fields.Integer(compute='_compute_document_count', string='Documentos')
    profile_completeness = fields.Integer(compute='_compute_profile_completeness', string='Perfil completo')

    _sql_constraints = [
        ('partner_unique', 'unique(partner_id)', 'Este contacto já possui um perfil de subempreiteiro.'),
    ]

    @api.depends('application_ids')
    def _compute_application_count(self):
        for profile in self:
            profile.application_count = len(profile.application_ids)

    @api.depends('document_attachment_ids', 'certification_attachment_ids')
    def _compute_document_count(self):
        for profile in self:
            profile.document_count = len(profile.document_attachment_ids) + len(profile.certification_attachment_ids)

    @api.depends(
        'company_name', 'legal_name', 'nuit', 'phone', 'email', 'supplier_type',
        'province', 'coverage_area', 'trades', 'service_pricing', 'team_size',
        'years_experience', 'equipment', 'certifications', 'presentation',
        'bank_name', 'document_attachment_ids', 'certification_attachment_ids',
    )
    def _compute_profile_completeness(self):
        tracked_fields = [
            'company_name', 'legal_name', 'nuit', 'phone', 'email', 'supplier_type',
            'province', 'coverage_area', 'trades', 'service_pricing', 'team_size',
            'years_experience', 'equipment', 'certifications', 'presentation',
            'bank_name',
        ]
        for profile in self:
            completed = sum(1 for field_name in tracked_fields if profile[field_name])
            if profile.document_attachment_ids:
                completed += 1
            if profile.certification_attachment_ids:
                completed += 1
            profile.profile_completeness = int((completed / (len(tracked_fields) + 2)) * 100)

    def _sync_supplier_partner(self):
        for profile in self:
            partner = profile.partner_id.commercial_partner_id
            values = {
                'name': profile.legal_name or profile.company_name,
                'email': profile.email,
                'phone': profile.phone,
                'street': profile.street,
                'city': profile.city,
            }
            if 'supplier_rank' in partner._fields:
                values['supplier_rank'] = max(partner.supplier_rank, 1)
            if 'vat' in partner._fields and profile.nuit:
                values['vat'] = profile.nuit
            partner.sudo().write(values)

    @api.model_create_multi
    def create(self, vals_list):
        profiles = super().create(vals_list)
        profiles._sync_supplier_partner()
        return profiles

    def write(self, vals):
        result = super().write(vals)
        supplier_fields = {
            'company_name', 'legal_name', 'email', 'phone', 'street', 'city', 'nuit',
        }
        if supplier_fields.intersection(vals):
            self._sync_supplier_partner()
        return result

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_suspend(self):
        self.write({'state': 'suspended'})


class GesSubcontractorJob(models.Model):
    _name = 'ges.subcontractor.job'
    _description = 'Oportunidade para Subempreiteiros GES'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'publish_date desc, id desc'

    name = fields.Char(string='Título', required=True, tracking=True)
    reference = fields.Char(string='Referência', default='Nova', copy=False, readonly=True, index=True)
    trade = fields.Char(string='Especialidade', required=True, tracking=True)
    location = fields.Char(string='Local', required=True, tracking=True)
    description = fields.Html(string='Descrição', required=True, sanitize=True)
    requirements = fields.Html(string='Requisitos', sanitize=True)
    deadline = fields.Date(string='Prazo de candidatura', tracking=True)
    publish_date = fields.Date(string='Publicação', default=fields.Date.today)
    state = fields.Selection([
        ('draft', 'Rascunho'),
        ('published', 'Publicada'),
        ('closed', 'Encerrada'),
    ], string='Estado', default='draft', required=True, tracking=True, index=True)
    application_ids = fields.One2many('ges.subcontractor.application', 'job_id', string='Candidaturas')
    application_count = fields.Integer(compute='_compute_application_count', string='Candidaturas')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'Nova') == 'Nova':
                vals['reference'] = self.env['ir.sequence'].next_by_code('ges.subcontractor.job') or 'Nova'
        return super().create(vals_list)

    @api.depends('application_ids')
    def _compute_application_count(self):
        for job in self:
            job.application_count = len(job.application_ids)

    def action_publish(self):
        self.write({'state': 'published', 'publish_date': fields.Date.today()})

    def action_close(self):
        self.write({'state': 'closed'})


class GesSubcontractorApplication(models.Model):
    _name = 'ges.subcontractor.application'
    _description = 'Candidatura de Subempreiteiro GES'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Referência', default='Nova', copy=False, readonly=True, index=True)
    job_id = fields.Many2one('ges.subcontractor.job', string='Oportunidade', required=True, ondelete='cascade', index=True, tracking=True)
    profile_id = fields.Many2one('ges.subcontractor.profile', string='Subempreiteiro', required=True, ondelete='cascade', index=True, tracking=True)
    partner_id = fields.Many2one(related='profile_id.partner_id', store=True, index=True, readonly=True)
    message = fields.Text(string='Mensagem de candidatura', required=True)
    availability_date = fields.Date(string='Disponível a partir de')
    proposed_team_size = fields.Integer(string='Equipa proposta', default=1)
    proposed_price = fields.Monetary(string='Proposta financeira')
    currency_id = fields.Many2one(related='profile_id.currency_id', store=True, readonly=True)
    execution_days = fields.Integer(string='Prazo de execução (dias)')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'ges_subcontractor_application_attachment_rel',
        'application_id', 'attachment_id', string='Anexos da candidatura',
    )
    state = fields.Selection([
        ('submitted', 'Recebida'),
        ('review', 'Em avaliação'),
        ('shortlisted', 'Pré-seleccionada'),
        ('accepted', 'Aceite'),
        ('rejected', 'Não seleccionada'),
        ('withdrawn', 'Retirada'),
    ], string='Estado', default='submitted', required=True, tracking=True, index=True)

    _sql_constraints = [
        ('job_profile_unique', 'unique(job_id, profile_id)', 'Já existe uma candidatura desta empresa para esta oportunidade.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nova') == 'Nova':
                vals['name'] = self.env['ir.sequence'].next_by_code('ges.subcontractor.application') or 'Nova'
        return super().create(vals_list)

    def action_review(self):
        self.write({'state': 'review'})

    def action_shortlist(self):
        self.write({'state': 'shortlisted'})

    def action_accept(self):
        self.write({'state': 'accepted'})

    def action_reject(self):
        self.write({'state': 'rejected'})
