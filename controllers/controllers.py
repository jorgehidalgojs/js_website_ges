# -*- coding: utf-8 -*-
import base64
from html import escape
from markupsafe import Markup
import json
import logging
import os

from odoo import fields, http
from odoo.http import request


_logger = logging.getLogger(__name__)


SOLUTION_GROUPS = [
    {
        'key': 'producao',
        'name': 'Produção',
        'intro': 'Capacidade industrial para fornecer materiais e componentes essenciais à obra.',
        'solutions': [
            ('fabrica-de-betao', 'Fábrica de Betão', 'Produção de betão para diferentes necessidades de construção, com foco na consistência, qualidade e disponibilidade.'),
            ('fabrica-de-blocos', 'Fábrica de Blocos', 'Produção de blocos para projectos de diferentes dimensões, assegurando regularidade e resistência.'),
            ('fabrica-de-vigotas', 'Fábrica de Vigotas', 'Produção de vigotas para sistemas estruturais, com atenção ao desempenho e à aplicação em obra.'),
            ('fabrica-de-aluminio', 'Fábrica de Alumínio', 'Produção de soluções em alumínio para construção e acabamento, adaptadas às necessidades do cliente.'),
            ('fabrica-de-moveis', 'Fábrica de Móveis', 'Produção de mobiliário funcional e personalizado para espaços corporativos, residenciais e institucionais.'),
            ('estruturas-metalicas', 'Fábrica de Estruturas Metálicas', 'Fabrico de estruturas metálicas para aplicações industriais, comerciais e de construção.'),
            ('ferros-de-construcao', 'Fábrica de Ferros de Construção', 'Preparação e fornecimento de ferro para responder às especificações estruturais da obra.'),
        ],
    },
    {
        'key': 'operacao',
        'name': 'Operação',
        'intro': 'Recursos, equipamentos e logística para garantir continuidade e eficiência no terreno.',
        'solutions': [
            ('transporte', 'Transporte', 'Soluções de transporte para materiais, equipamentos e apoio às operações no terreno.'),
            ('aluguer-de-equipamentos', 'Aluguer de Equipamentos', 'Disponibilização de equipamentos para apoiar diferentes fases e necessidades da obra.'),
            ('aluguer-de-andaimes', 'Aluguer de Andaimes', 'Sistemas de andaimes para acesso e trabalho em altura, adequados às exigências de cada projecto.'),
            ('armazem-e-logistica', 'Armazém e Logística', 'Recepção, organização, armazenamento e movimentação de materiais para apoiar a continuidade operacional.'),
            ('ferramentas', 'Ferramentas', 'Disponibilização de ferramentas adequadas às diferentes actividades de construção e manutenção.'),
        ],
    },
    {
        'key': 'execucao',
        'name': 'Execução',
        'intro': 'Estrutura humana e operacional para transformar planeamento em obra realizada.',
        'solutions': [
            ('mao-de-obra', 'Força de Trabalho — Mão de Obra', 'Disponibilização de profissionais para apoiar a execução de tarefas especializadas e operacionais.'),
            ('estaleiros', 'Estaleiros', 'Organização e apoio à instalação de estaleiros para garantir melhores condições de execução e controlo.'),
            ('pedreira', 'Pedreira', 'Extracção e fornecimento de agregados e matérias-primas para construção e produção.'),
        ],
    },
]

CATALOG_GROUPS = [
    {
        'key': 'producao',
        'name': 'Produção de materiais',
        'intro': 'Materiais e componentes fabricados/fornecidos para estruturar a obra desde a base.',
        'icon': 'fa-industry',
        'products': [
            {
                'sku': 'GES-BET',
                'name': 'Betão pronto',
                'capacity': 'Fábrica de Betão',
                'description': 'Betão para fundações, lajes, vigas, pilares, pavimentos e elementos estruturais, com composição validada conforme aplicação.',
                'applications': 'Obras residenciais, industriais, comerciais e infraestruturas.',
                'formats': ['m³ sob pedido', 'Traços por aplicação', 'Entrega em obra'],
                'badge': 'Estrutural',
                'icon': 'fa-cube',
            },
            {
                'sku': 'GES-BLC',
                'name': 'Blocos de construção',
                'capacity': 'Fábrica de Blocos',
                'description': 'Blocos para alvenaria e vedação, produzidos para garantir regularidade, resistência e boa produtividade no assentamento.',
                'applications': 'Paredes interiores, exteriores, muros e divisórias técnicas.',
                'formats': ['Blocos 40×20', 'Blocos 39×19', 'Quantidades por obra'],
                'badge': 'Alvenaria',
                'icon': 'fa-th-large',
            },
            {
                'sku': 'GES-VGT',
                'name': 'Vigotas e elementos pré-fabricados',
                'capacity': 'Fábrica de Vigotas',
                'description': 'Elementos para sistemas de laje e soluções estruturais leves, orientados para montagem mais rápida e controlada.',
                'applications': 'Lajes, coberturas técnicas e estruturas de suporte.',
                'formats': ['Medidas por projecto', 'Pré-fabricação', 'Apoio técnico'],
                'badge': 'Pré-fabricado',
                'icon': 'fa-bars',
            },
            {
                'sku': 'GES-FER',
                'name': 'Ferro de construção preparado',
                'capacity': 'Fábrica de Ferros de Construção',
                'description': 'Preparação e fornecimento de aço/ferro para armaduras, cortes e necessidades estruturais de obra.',
                'applications': 'Fundações, pilares, vigas, lajes e reforços estruturais.',
                'formats': ['Varões', 'Corte/dobra', 'Por especificação'],
                'badge': 'Armadura',
                'icon': 'fa-sliders',
            },
            {
                'sku': 'GES-MET',
                'name': 'Estruturas metálicas',
                'capacity': 'Fábrica de Estruturas Metálicas',
                'description': 'Fabrico de estruturas metálicas para suporte, cobertura, reforço e soluções industriais ou comerciais.',
                'applications': 'Galpões, coberturas, plataformas, reforços e estruturas especiais.',
                'formats': ['Fabrico por desenho', 'Montagem coordenada', 'Acabamentos'],
                'badge': 'Metálica',
                'icon': 'fa-building-o',
            },
            {
                'sku': 'GES-ALU',
                'name': 'Soluções em alumínio',
                'capacity': 'Fábrica de Alumínio',
                'description': 'Caixilharia e componentes em alumínio para acabamentos duráveis, funcionais e alinhados ao projecto.',
                'applications': 'Janelas, portas, fachadas leves, divisórias e acabamentos.',
                'formats': ['Por medida', 'Instalação', 'Acabamento técnico'],
                'badge': 'Acabamento',
                'icon': 'fa-window-maximize',
            },
            {
                'sku': 'GES-MOV',
                'name': 'Mobiliário técnico e corporativo',
                'capacity': 'Fábrica de Móveis',
                'description': 'Mobiliário funcional para espaços corporativos, comerciais, institucionais e residenciais.',
                'applications': 'Escritórios, recepções, salas técnicas, alojamentos e interiores.',
                'formats': ['Personalizado', 'Por ambiente', 'Instalação'],
                'badge': 'Interiores',
                'icon': 'fa-briefcase',
            },
        ],
    },
    {
        'key': 'operacao',
        'name': 'Operação, logística e equipamentos',
        'intro': 'Recursos operacionais para manter a obra abastecida, organizada e produtiva.',
        'icon': 'fa-truck',
        'products': [
            {
                'sku': 'GES-TRP',
                'name': 'Transporte de materiais',
                'capacity': 'Transporte',
                'description': 'Transporte planeado de materiais, equipamentos e componentes, com coordenação conforme volume, distância e acesso.',
                'applications': 'Entregas em obra, transferências, abastecimento e apoio logístico.',
                'formats': ['Por viagem', 'Por rota', 'Carga programada'],
                'badge': 'Logística',
                'icon': 'fa-truck',
            },
            {
                'sku': 'GES-EQP',
                'name': 'Aluguer de equipamentos',
                'capacity': 'Aluguer de Equipamentos',
                'description': 'Equipamentos para apoiar diferentes fases da obra, reduzindo paragens e aumentando produtividade operacional.',
                'applications': 'Movimentação, apoio à execução, preparação e manutenção.',
                'formats': ['Diário', 'Semanal', 'Por projecto'],
                'badge': 'Equipamentos',
                'icon': 'fa-cogs',
            },
            {
                'sku': 'GES-AND',
                'name': 'Sistemas de andaimes',
                'capacity': 'Aluguer de Andaimes',
                'description': 'Andaimes para acesso, trabalho em altura e segurança operacional, dimensionados conforme a necessidade da obra.',
                'applications': 'Fachadas, manutenção, pintura, instalações e reabilitação.',
                'formats': ['Por m²', 'Por período', 'Montagem assistida'],
                'badge': 'Acesso',
                'icon': 'fa-sort-amount-asc',
            },
            {
                'sku': 'GES-ARM',
                'name': 'Armazém e logística',
                'capacity': 'Armazém e Logística',
                'description': 'Apoio de armazenamento, organização e movimentação para controlar materiais e reduzir rupturas na obra.',
                'applications': 'Stock temporário, kits de obra, recepção e expedição.',
                'formats': ['Gestão de stock', 'Picking', 'Entrega coordenada'],
                'badge': 'Controlo',
                'icon': 'fa-archive',
            },
            {
                'sku': 'GES-FRM',
                'name': 'Ferramentas de obra',
                'capacity': 'Ferramentas',
                'description': 'Ferramentas e apoio técnico para actividades de construção, manutenção, instalação e acabamento.',
                'applications': 'Equipas de obra, manutenção, acabamentos e intervenções rápidas.',
                'formats': ['Kit por actividade', 'Por período', 'Sob solicitação'],
                'badge': 'Apoio',
                'icon': 'fa-wrench',
            },
        ],
    },
    {
        'key': 'execucao',
        'name': 'Execução e obra',
        'intro': 'Serviços de campo para transformar materiais, logística e planeamento em obra entregue.',
        'icon': 'fa-building',
        'products': [
            {
                'sku': 'GES-MOB',
                'name': 'Mão de obra especializada',
                'capacity': 'Força de Trabalho — Mão de Obra',
                'description': 'Equipas e profissionais para execução de tarefas específicas, reforço operacional e avanço controlado da obra.',
                'applications': 'Construção civil, acabamentos, apoio técnico e manutenção.',
                'formats': ['Por equipa', 'Por actividade', 'Por período'],
                'badge': 'Execução',
                'icon': 'fa-users',
            },
            {
                'sku': 'GES-EST',
                'name': 'Instalação e apoio a estaleiros',
                'capacity': 'Estaleiros',
                'description': 'Apoio na organização de estaleiros, áreas de trabalho, fluxos de materiais e condições operacionais.',
                'applications': 'Arranque de obra, projectos temporários, organização e suporte.',
                'formats': ['Planeamento', 'Instalação', 'Apoio contínuo'],
                'badge': 'Obra',
                'icon': 'fa-map-signs',
            },
            {
                'sku': 'GES-PED',
                'name': 'Agregados e materiais de pedreira',
                'capacity': 'Pedreira',
                'description': 'Fornecimento de agregados e matérias-primas para produção, fundações, enchimentos e infraestruturas.',
                'applications': 'Betão, bases, aterros, drenagem, vias e preparação de terreno.',
                'formats': ['Por tonelada', 'Por m³', 'Entrega em obra'],
                'badge': 'Agregados',
                'icon': 'fa-diamond',
            },
        ],
    },
]

GES_CANONICAL_DOMAIN = 'generalexpress.co.mz'
GES_DEFAULT_BASE_URL = 'https://www.generalexpress.co.mz'


SEO_PAGES = {
    'home': {
        'title': 'GES Moçambique | Construção, Betão, Blocos e Infraestruturas',
        'description': 'General Express Service em Moçambique: construção, betão pronto, blocos, vigotas, ferro, transporte, equipamentos, logística e execução de obras.',
        'keywords': 'GES Moçambique, construção em Moçambique, empresa de construção Maputo, betão pronto Maputo, blocos de construção, infraestruturas Moçambique',
    },
    'about': {
        'title': 'Sobre a GES | Empresa de Construção em Maputo e Moçambique',
        'description': 'Conheça a General Express Service, empresa moçambicana de construção, materiais, logística, equipamentos e infraestruturas com sede em Maputo.',
        'keywords': 'General Express Service, GES Maputo, empresa de construção em Maputo, construção civil Moçambique, empreiteiro Moçambique',
    },
    'solutions': {
        'title': 'Soluções de Construção, Materiais e Equipamentos | GES Moçambique',
        'description': 'Explore 15 soluções GES: betão, blocos, vigotas, ferro, estruturas metálicas, transporte, equipamentos, andaimes, logística, mão de obra e pedreira.',
        'keywords': 'soluções de construção Moçambique, materiais de construção Maputo, aluguer de equipamentos Maputo, andaimes Moçambique, logística de obra',
    },
    'tools': {
        'title': 'Calculadoras de Obra Online | Betão, Blocos e Transporte GES',
        'description': 'Ferramentas digitais GES para calcular betão, blocos, transporte, preparação de obra e soluções integradas para projectos em Moçambique.',
        'keywords': 'calculadora de betão Moçambique, calculadora de blocos, orçamento de construção Maputo, cotação materiais construção',
    },
    'catalog': {
        'title': 'Catálogo Online GES | Betão, Blocos, Ferro, Andaimes e Equipamentos',
        'description': 'Catálogo interactivo GES por capacidade: betão pronto, blocos, vigotas, ferro, estruturas metálicas, transporte, equipamentos, andaimes, mão de obra e logística.',
        'keywords': 'catálogo materiais construção Moçambique, betão pronto Maputo, blocos Maputo, ferro de construção, aluguer de andaimes Maputo',
    },
    'projects': {
        'title': 'Projectos de Construção e Infraestruturas em Moçambique | GES',
        'description': 'Projectos GES em Moçambique com coordenação de engenharia, produção de materiais, logística, equipamentos e execução no terreno.',
        'keywords': 'projectos de construção Moçambique, obras em Maputo, infraestruturas Moçambique, portfólio construção',
    },
    'news': {
        'title': 'Notícias, Projectos e Comunidade | GES Moçambique',
        'description': 'Acompanhe projectos, operações, iniciativas comunitárias e conhecimento técnico da General Express Service.',
        'keywords': 'notícias construção Moçambique, GES notícias, obras Moçambique, comunidade construção Maputo',
    },
    'social': {
        'title': 'Contribuição Social em Moçambique | GES e SOS Palace',
        'description': 'Conheça a contribuição social da GES e a parceria com a SOS Palace para apoiar famílias, inclusão social, voluntariado e impacto comunitário em Moçambique.',
        'keywords': 'contribuição social Moçambique, responsabilidade social empresarial Maputo, GES SOS Palace, apoio comunitário Moçambique',
    },
    'environment': {
        'title': 'Contribuição Ambiental | Construção Sustentável GES Moçambique',
        'description': 'Conheça a contribuição ambiental da GES: construção responsável, uso eficiente de materiais, logística consciente, gestão de resíduos e práticas sustentáveis.',
        'keywords': 'construção sustentável Moçambique, contribuição ambiental, sustentabilidade na construção, gestão de resíduos obra Maputo',
    },
    'contact': {
        'title': 'Pedido de Cotação de Construção e Materiais | GES Moçambique',
        'description': 'Contacte a GES em Maputo e peça cotação para construção, reabilitação, betão, blocos, ferro, equipamentos, transporte ou logística em Moçambique.',
        'keywords': 'pedido de cotação construção Moçambique, contacto GES Maputo, orçamento obra Maputo, cotação betão blocos equipamentos',
    },
}

PAGE_PATHS = {
    'home': '/',
    'about': '/ges/sobre-nos',
    'solutions': '/ges/solucoes',
    'tools': '/ges/ferramentas',
    'catalog': '/ges/catalogo',
    'projects': '/ges/projectos',
    'news': '/ges/noticias',
    'social': '/ges/contribuicao-social',
    'environment': '/ges/contribuicao-ambiental',
    'contact': '/ges/contactos',
}

PAGE_LABELS = {
    'home': 'Início',
    'about': 'Sobre nós',
    'solutions': 'Soluções',
    'tools': 'Ferramentas',
    'catalog': 'Catálogo',
    'projects': 'Projectos',
    'news': 'Notícias',
    'social': 'Contribuição social',
    'environment': 'Contribuição ambiental',
    'contact': 'Contactos',
}


def _ges_public_paths():
    paths = [PAGE_PATHS[key] for key in (
        'home', 'about', 'solutions', 'catalog', 'tools', 'projects',
        'news', 'social', 'environment', 'contact',
    )]
    paths.extend('/ges/solucoes/%s' % solution['slug'] for solution in _solutions())
    return paths


def _solutions():
    result = []
    number = 1
    for group in SOLUTION_GROUPS:
        for slug, name, summary in group['solutions']:
            result.append({
                'slug': slug,
                'name': name,
                'summary': summary,
                'group': group['name'],
                'group_key': group['key'],
                'number': '%02d' % number,
            })
            number += 1
    return result


def sitemap_solutions(env, rule, qs):
    for solution in _solutions():
        loc = '/ges/solucoes/%s' % solution['slug']
        if not qs or qs.lower() in loc.lower():
            yield {'loc': loc}


def _jsonld(data):
    return Markup(json.dumps(data, ensure_ascii=False, separators=(',', ':')))


def _site_base_url():
    """Return the public GES domain for canonical SEO URLs.

    In production, any host containing generalexpress.co.mz is preserved
    (for example www.generalexpress.co.mz or staging.generalexpress.co.mz).
    In local/dev environments, canonical metadata still points to the official
    public domain so crawlers do not learn localhost/IP URLs.
    """
    if not request:
        return GES_DEFAULT_BASE_URL
    host = (request.httprequest.host or '').split(':', 1)[0].lower()
    if GES_CANONICAL_DOMAIN in host:
        return request.httprequest.url_root.rstrip('/')
    return GES_DEFAULT_BASE_URL


def _apply_structured_data(values, canonical_path, breadcrumb_items):
    base_url = _site_base_url()
    canonical_url = base_url + canonical_path
    organization_id = base_url + '/#organization'
    website_id = base_url + '/#website'
    webpage_id = canonical_url + '#webpage'
    graph = [
        {
            '@type': ['Organization', 'LocalBusiness'],
            '@id': organization_id,
            'name': 'General Express Service',
            'alternateName': 'GES',
            'url': base_url + '/',
            'logo': {
                '@type': 'ImageObject',
                'url': base_url + '/js_website_ges/static/src/img/ges-logo.png',
                'width': 1550,
                'height': 620,
            },
            'image': base_url + '/js_website_ges/static/src/img/hero-integrated.webp',
            'description': 'Soluções integradas para construção, reabilitação e manutenção em Moçambique.',
            'email': 'comercial@generalexpress.co.mz',
            'telephone': ['+258858900313', '+258849102552'],
            'taxID': '400130264',
            'address': {
                '@type': 'PostalAddress',
                'streetAddress': 'Av. de Moçambique, n.º 2298',
                'addressLocality': 'Maputo',
                'postalCode': '1102',
                'addressCountry': 'MZ',
            },
            'areaServed': {'@type': 'Country', 'name': 'Moçambique'},
            'geo': {
                '@type': 'GeoCoordinates',
                'latitude': -25.9682,
                'longitude': 32.5732,
            },
            'priceRange': '$$',
            'knowsAbout': [
                'Construção civil',
                'Betão pronto',
                'Blocos de construção',
                'Vigotas',
                'Ferro de construção',
                'Aluguer de equipamentos',
                'Transporte de materiais',
                'Infraestruturas em Moçambique',
            ],
            'hasOfferCatalog': {
                '@type': 'OfferCatalog',
                'name': 'Soluções GES para construção em Moçambique',
                'itemListElement': [
                    {
                        '@type': 'Offer',
                        'itemOffered': {
                            '@type': 'Service',
                            'name': solution['name'],
                            'description': solution['summary'],
                        },
                    }
                    for solution in _solutions()
                ],
            },
        },
        {
            '@type': 'WebSite',
            '@id': website_id,
            'url': base_url + '/',
            'name': 'General Express Service',
            'alternateName': 'GES Moçambique',
            'inLanguage': 'pt-MZ',
            'publisher': {'@id': organization_id},
            'potentialAction': {
                '@type': 'SearchAction',
                'target': base_url + '/ges/catalogo?search={search_term_string}',
                'query-input': 'required name=search_term_string',
            },
        },
        {
            '@type': 'WebPage',
            '@id': webpage_id,
            'url': canonical_url,
            'name': values['seo_title'],
            'description': values['seo_description'],
            'inLanguage': 'pt-MZ',
            'isPartOf': {'@id': website_id},
            'about': {'@id': organization_id},
            'primaryImageOfPage': {
                '@type': 'ImageObject',
                'url': base_url + values['seo_image'],
            },
        },
    ]
    if len(breadcrumb_items) > 1:
        graph.append({
            '@type': 'BreadcrumbList',
            '@id': canonical_url + '#breadcrumb',
            'itemListElement': [
                {
                    '@type': 'ListItem',
                    'position': index,
                    'name': item['name'],
                    'item': base_url + item['href'] if item.get('href') else canonical_url,
                }
                for index, item in enumerate(breadcrumb_items, 1)
            ],
        })
    values['seo_base_schema_json'] = _jsonld({
        '@context': 'https://schema.org',
        '@graph': graph,
    })


def _page_values(active):
    canonical_path = PAGE_PATHS[active]
    breadcrumb_items = [] if active == 'home' else [
        {'name': 'Início', 'href': '/'},
        {'name': PAGE_LABELS[active], 'href': None},
    ]
    values = {
        'active_page': active,
        'solution_groups': SOLUTION_GROUPS,
        'solutions': _solutions(),
        'seo_keywords': SEO_PAGES[active].get('keywords', 'construção em Moçambique, betão, blocos, materiais de construção, aluguer de equipamentos, logística, mão de obra, infraestruturas'),
        'seo_schema_json': None,
        'seo_image': '/js_website_ges/static/src/img/hero-integrated.webp',
        'seo_image_alt': 'Capacidade integrada da General Express Service em Moçambique',
        'seo_canonical_path': canonical_path,
        'seo_base_url': _site_base_url(),
        'seo_canonical_url': _site_base_url() + canonical_path,
        'breadcrumb_items': breadcrumb_items,
    }
    values.update({
        'seo_title': SEO_PAGES[active]['title'],
        'seo_description': SEO_PAGES[active]['description'],
    })
    _apply_structured_data(values, canonical_path, breadcrumb_items)
    return values


class GesWebsite(http.Controller):

    @http.route('/robots.txt', type='http', auth='public', website=False, sitemap=False)
    def robots_txt(self, **kwargs):
        base_url = _site_base_url()
        body = '\n'.join([
            'User-agent: *',
            'Allow: /',
            'Disallow: /web/login',
            'Disallow: /web/database',
            'Disallow: /my/',
            'Disallow: /mail/',
            'Disallow: /website/info',
            'Sitemap: %s/sitemap.xml' % base_url,
            'Sitemap: %s/ges/sitemap.xml' % base_url,
            '',
        ])
        return request.make_response(body, headers=[
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Cache-Control', 'public, max-age=3600'),
        ])

    @http.route('/ges/sitemap.xml', type='http', auth='public', website=False, sitemap=False)
    def ges_sitemap_xml(self, **kwargs):
        base_url = _site_base_url()
        today = fields.Date.today().isoformat()
        high_priority = {'/', '/ges/solucoes', '/ges/catalogo', '/ges/contactos'}
        urlset = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for path in _ges_public_paths():
            priority = '1.0' if path == '/' else ('0.9' if path in high_priority else '0.7')
            changefreq = 'weekly' if path in high_priority else 'monthly'
            urlset.extend([
                '  <url>',
                '    <loc>%s</loc>' % escape(base_url + path, quote=True),
                '    <lastmod>%s</lastmod>' % today,
                '    <changefreq>%s</changefreq>' % changefreq,
                '    <priority>%s</priority>' % priority,
                '  </url>',
            ])
        urlset.append('</urlset>')
        return request.make_response('\n'.join(urlset), headers=[
            ('Content-Type', 'application/xml; charset=utf-8'),
            ('Cache-Control', 'public, max-age=3600'),
        ])

    @http.route('/', type='http', auth='public', website=True, sitemap=True)
    def home(self, **kwargs):
        return request.render('js_website_ges.homepage', _page_values('home'))

    @http.route('/ges', type='http', auth='public', website=True, sitemap=False)
    def home_alias(self, **kwargs):
        return request.redirect('/', code=301)

    @http.route('/ges/sobre-nos', type='http', auth='public', website=True, sitemap=True)
    def about(self, **kwargs):
        return request.render('js_website_ges.about_page', _page_values('about'))

    @http.route('/ges/solucoes', type='http', auth='public', website=True, sitemap=True)
    def solutions(self, **kwargs):
        return request.render('js_website_ges.solutions_page', _page_values('solutions'))

    @http.route('/ges/ferramentas', type='http', auth='public', website=True, sitemap=True)
    def tools(self, **kwargs):
        values = _page_values('tools')
        values['seo_schema_json'] = _jsonld({
            '@context': 'https://schema.org',
            '@type': 'WebApplication',
            'name': 'Ferramentas de Obra GES',
            'applicationCategory': 'BusinessApplication',
            'operatingSystem': 'Web',
            'description': values['seo_description'],
            'provider': {
                '@id': _site_base_url() + '/#organization',
            },
            'url': values['seo_canonical_url'],
        })
        return request.render('js_website_ges.tools_page', values)

    @http.route('/ges/catalogo', type='http', auth='public', website=True, sitemap=True)
    def catalog(self, **kwargs):
        values = _page_values('catalog')
        catalog_products = [
            dict(product, group_key=group['key'], group_name=group['name'], group_icon=group['icon'])
            for group in CATALOG_GROUPS
            for product in group['products']
        ]
        values.update({
            'catalog_groups': CATALOG_GROUPS,
            'catalog_products': catalog_products,
        })
        values['seo_schema_json'] = _jsonld({
            '@context': 'https://schema.org',
            '@type': 'CollectionPage',
            'name': 'Catálogo Online GES',
            'description': values['seo_description'],
            'hasPart': [
                {
                    '@type': 'Product',
                    'name': product['name'],
                    'description': product['description'],
                    'category': product['capacity'],
                    'brand': {'@type': 'Brand', 'name': 'GES'},
                }
                for product in catalog_products
            ],
            'provider': {
                '@id': _site_base_url() + '/#organization',
            },
            'url': values['seo_canonical_url'],
        })
        return request.render('js_website_ges.catalog_page', values)

    @http.route('/ges/solucoes/<string:slug>', type='http', auth='public', website=True, sitemap=sitemap_solutions)
    def solution(self, slug, **kwargs):
        solution = next((item for item in _solutions() if item['slug'] == slug), None)
        if not solution:
            return request.not_found()
        values = _page_values('solutions')
        values['solution'] = solution
        values['seo_title'] = '%s em Moçambique | GES' % solution['name']
        values['seo_description'] = '%s Conheça a capacidade integrada e solicite informação à equipa GES.' % solution['summary']
        values['breadcrumb_items'] = [
            {'name': 'Início', 'href': '/'},
            {'name': 'Soluções', 'href': '/ges/solucoes'},
            {'name': solution['name'], 'href': None},
        ]
        _apply_structured_data(values, '/ges/solucoes/%s' % slug, values['breadcrumb_items'])
        values['seo_schema_json'] = _jsonld({
            '@context': 'https://schema.org',
            '@type': 'Service',
            'name': solution['name'],
            'description': solution['summary'],
            'areaServed': {'@type': 'Country', 'name': 'Moçambique'},
            'provider': {
                '@id': _site_base_url() + '/#organization',
            },
            'url': values['seo_canonical_url'],
        })
        return request.render('js_website_ges.solution_detail_page', values)

    @http.route('/ges/projectos', type='http', auth='public', website=True, sitemap=True)
    def projects(self, **kwargs):
        return request.render('js_website_ges.projects_page', _page_values('projects'))

    @http.route('/ges/noticias', type='http', auth='public', website=True, sitemap=True)
    def news(self, **kwargs):
        return request.render('js_website_ges.news_page', _page_values('news'))

    @http.route('/ges/contribuicao-social', type='http', auth='public', website=True, sitemap=True)
    def social_contribution(self, **kwargs):
        values = _page_values('social')
        values['seo_schema_json'] = _jsonld({
            '@context': 'https://schema.org',
            '@type': 'AboutPage',
            'name': 'Contribuição Social GES',
            'description': values['seo_description'],
            'about': {
                '@type': 'NGO',
                'name': 'SOS Palace',
                'url': 'https://sos.palace.co.mz/',
            },
            'provider': {
                '@id': _site_base_url() + '/#organization',
            },
            'url': values['seo_canonical_url'],
        })
        return request.render('js_website_ges.social_contribution_page', values)

    @http.route('/ges/contribuicao-ambiental', type='http', auth='public', website=True, sitemap=True)
    def environmental_contribution(self, **kwargs):
        values = _page_values('environment')
        values['seo_schema_json'] = _jsonld({
            '@context': 'https://schema.org',
            '@type': 'AboutPage',
            'name': 'Contribuição Ambiental GES',
            'description': values['seo_description'],
            'provider': {
                '@id': _site_base_url() + '/#organization',
            },
            'url': values['seo_canonical_url'],
        })
        return request.render('js_website_ges.environmental_contribution_page', values)

    @http.route('/ges/contactos', type='http', auth='public', website=True, sitemap=True)
    def contact(self, **kwargs):
        values = _page_values('contact')
        values['sent'] = kwargs.get('sent') == '1'
        values['error'] = kwargs.get('error')
        values['selected_solution'] = kwargs.get('solution')
        return request.render('js_website_ges.contact_page', values)

    @http.route('/ges/contactos/enviar', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def contact_send(self, **post):
        if post.get('website'):
            return request.redirect('/ges/contactos?sent=1')

        required = ('name', 'email', 'phone', 'message')
        if any(not (post.get(field) or '').strip() for field in required):
            return request.redirect('/ges/contactos?error=required')

        solution = post.get('solution') or 'Não indicada'
        safe_values = [escape(str(value or '')) for value in (
            post.get('name'), post.get('company'), post.get('phone'),
            post.get('email'), post.get('location'), solution,
            post.get('deadline'), post.get('message'),
        )]
        safe_values[-1] = safe_values[-1].replace('\n', '<br/>')
        body = """
            <p><strong>Novo pedido de cotação recebido pelo website GES.</strong></p>
            <p><strong>Nome:</strong> %s<br/>
            <strong>Empresa:</strong> %s<br/>
            <strong>Telefone:</strong> %s<br/>
            <strong>E-mail:</strong> %s<br/>
            <strong>Localização:</strong> %s<br/>
            <strong>Solução:</strong> %s<br/>
            <strong>Prazo previsto:</strong> %s</p>
            <p><strong>Necessidade:</strong><br/>%s</p>
        """ % tuple(safe_values)

        upload = request.httprequest.files.get('attachment')
        upload_data = upload.read() if upload and upload.filename else None
        if upload_data and len(upload_data) > 10 * 1024 * 1024:
            return request.redirect('/ges/contactos?error=attachment')

        mail = request.env['mail.mail'].sudo().create({
            'subject': 'Pedido de cotação — %s' % post.get('name'),
            'body_html': body,
            'email_to': 'comercial@generalexpress.co.mz',
            'email_from': 'website@generalexpress.co.mz',
            'reply_to': post.get('email'),
        })

        if upload_data:
            attachment = request.env['ir.attachment'].sudo().create({
                'name': os.path.basename(upload.filename.replace('\\', '/')),
                'datas': base64.b64encode(upload_data),
                'res_model': 'mail.mail',
                'res_id': mail.id,
            })
            mail.attachment_ids = [(4, attachment.id)]

        try:
            mail.send()
        except Exception:
            _logger.exception('Não foi possível enviar o pedido de cotação GES')
            return request.redirect('/ges/contactos?error=send')
        return request.redirect('/ges/contactos?sent=1')
