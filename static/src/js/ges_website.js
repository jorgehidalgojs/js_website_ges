odoo.define('js_website_ges.frontend', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    publicWidget.registry.GesWebsite = publicWidget.Widget.extend({
        selector: '.ges-page',
        events: {
            'click .ges-menu-toggle': '_onMenuToggle',
            'click .ges-nav a': '_onNavClick',
            'click [data-ges-slide-to]': '_onHeroDot',
            'click .ges-hero-arrow--prev': '_onHeroPrev',
            'click .ges-hero-arrow--next': '_onHeroNext',
            'mouseenter .ges-hero-slider': '_pauseHero',
            'mouseleave .ges-hero-slider': '_resumeHero',
            'focusin .ges-hero-slider': '_pauseHero',
            'focusout .ges-hero-slider': '_resumeHero',
            'touchstart .ges-hero-slider': '_onHeroTouchStart',
            'touchend .ges-hero-slider': '_onHeroTouchEnd',
            'click [data-ges-solution-filter]': '_onSolutionFilter',
            'click [data-ges-capability]': '_onCapabilityChange',
            'mouseenter [data-ges-capability]': '_onCapabilityChange',
            'mousemove [data-ges-parallax]': '_onParallaxMove',
            'mouseleave [data-ges-parallax]': '_onParallaxLeave',
        },

        start: function () {
            this.header = this.el.querySelector('.ges-header');
            this.nav = this.el.querySelector('.ges-nav');
            this.toggle = this.el.querySelector('.ges-menu-toggle');
            this.hero = this.el.querySelector('.ges-hero-slider');
            this.heroSlides = this.el.querySelectorAll('[data-ges-slide]');
            this.heroDots = this.el.querySelectorAll('[data-ges-slide-to]');
            this.heroIndex = 0;
            this._scrollHandler = this._onScroll.bind(this);
            this._keyHandler = this._onKeyDown.bind(this);
            this._resizeHandler = this._onResize.bind(this);
            window.addEventListener('scroll', this._scrollHandler, {passive: true});
            window.addEventListener('resize', this._resizeHandler, {passive: true});
            document.addEventListener('keydown', this._keyHandler);
            this._onScroll();
            this._onResize();
            if (this.heroSlides.length) {
                this._showHero(0);
            }
            this._startHero();
            this._initReveal();
            this._initSolutionFilter();
            this._initLazyBackgrounds();
            this._initCounters();
            if (this.el.querySelector('[data-ges-capability-showcase]')) {
                this._showCapability('producao');
            }
            return this._super.apply(this, arguments);
        },

        destroy: function () {
            window.removeEventListener('scroll', this._scrollHandler);
            window.removeEventListener('resize', this._resizeHandler);
            document.removeEventListener('keydown', this._keyHandler);
            document.body.classList.remove('ges-menu-open');
            window.clearInterval(this.heroTimer);
            if (this.revealObserver) {
                this.revealObserver.disconnect();
            }
            if (this.lazyBackgroundObserver) {
                this.lazyBackgroundObserver.disconnect();
            }
            if (this.counterObserver) {
                this.counterObserver.disconnect();
            }
            this._super.apply(this, arguments);
        },

        _onScroll: function () {
            if (this.header) {
                this.header.classList.toggle('is-fixed', window.scrollY > 24);
            }
        },

        _onMenuToggle: function () {
            this._setMenu(!this.nav.classList.contains('is-open'));
        },

        _onNavClick: function () {
            this._setMenu(false);
        },

        _setMenu: function (open) {
            if (!this.nav || !this.toggle) {
                return;
            }
            this.nav.classList.toggle('is-open', open);
            this.header.classList.toggle('is-menu-open', open);
            document.body.classList.toggle('ges-menu-open', open);
            this.toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            this.toggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
            if (window.innerWidth <= 991) {
                this.nav.setAttribute('aria-hidden', open ? 'false' : 'true');
            } else {
                this.nav.removeAttribute('aria-hidden');
            }
            if (open) {
                this._pauseHero();
            } else {
                this._resumeHero();
            }
        },

        _onKeyDown: function (event) {
            if (event.key === 'Escape' && this.nav && this.nav.classList.contains('is-open')) {
                this._setMenu(false);
                this.toggle.focus();
                return;
            }
            if (event.key === 'Tab' && this.nav && this.nav.classList.contains('is-open')) {
                var focusable = [this.toggle].concat(Array.prototype.slice.call(this.nav.querySelectorAll('summary, a')));
                var first = focusable[0];
                var last = focusable[focusable.length - 1];
                if (event.shiftKey && document.activeElement === first) {
                    event.preventDefault();
                    last.focus();
                } else if (!event.shiftKey && document.activeElement === last) {
                    event.preventDefault();
                    first.focus();
                }
            }
        },

        _onResize: function () {
            if (!this.nav || !this.toggle) {
                return;
            }
            if (window.innerWidth > 991) {
                this._setMenu(false);
                this.nav.removeAttribute('aria-hidden');
            } else if (!this.nav.classList.contains('is-open')) {
                this.nav.setAttribute('aria-hidden', 'true');
            }
        },

        _startHero: function () {
            if (!this.hero || this.heroSlides.length < 2 || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                return;
            }
            window.clearInterval(this.heroTimer);
            this.heroTimer = window.setInterval(function () {
                this._showHero((this.heroIndex + 1) % this.heroSlides.length);
            }.bind(this), 7000);
        },

        _showHero: function (index) {
            this.heroIndex = (index + this.heroSlides.length) % this.heroSlides.length;
            this._loadHero(this.heroIndex);
            this._loadHero((this.heroIndex + 1) % this.heroSlides.length);
            Array.prototype.forEach.call(this.heroSlides, function (slide, slideIndex) {
                var active = slideIndex === this.heroIndex;
                slide.classList.toggle('is-active', active);
                slide.setAttribute('aria-hidden', active ? 'false' : 'true');
                Array.prototype.forEach.call(slide.querySelectorAll('a, button'), function (control) {
                    control.setAttribute('tabindex', active ? '0' : '-1');
                });
            }.bind(this));
            Array.prototype.forEach.call(this.heroDots, function (dot, dotIndex) {
                var active = dotIndex === this.heroIndex;
                dot.classList.toggle('is-active', active);
                if (active) {
                    dot.setAttribute('aria-current', 'true');
                } else {
                    dot.removeAttribute('aria-current');
                }
            }.bind(this));
            var counter = this.el.querySelector('.ges-hero-current');
            if (counter) {
                counter.textContent = String(this.heroIndex + 1).padStart(2, '0');
            }
        },

        _loadHero: function (index) {
            var slide = this.heroSlides[index];
            if (!slide) {
                return;
            }
            var media = slide.querySelector('[data-ges-src]');
            if (media && !media.getAttribute('data-ges-loaded')) {
                media.setAttribute('loading', 'eager');
                if (media.getAttribute('data-ges-srcset')) {
                    media.setAttribute('srcset', media.getAttribute('data-ges-srcset'));
                    media.removeAttribute('data-ges-srcset');
                }
                media.setAttribute('src', media.getAttribute('data-ges-src'));
                media.removeAttribute('data-ges-src');
                media.setAttribute('data-ges-loaded', 'true');
            }
        },

        _onHeroDot: function (event) {
            this._showHero(parseInt(event.currentTarget.getAttribute('data-ges-slide-to'), 10));
            this._startHero();
        },

        _onHeroPrev: function () {
            this._showHero(this.heroIndex - 1);
            this._startHero();
        },

        _onHeroNext: function () {
            this._showHero(this.heroIndex + 1);
            this._startHero();
        },

        _onHeroTouchStart: function (event) {
            var touch = event.originalEvent.touches[0];
            this.heroTouchX = touch.clientX;
            this.heroTouchY = touch.clientY;
            this._pauseHero();
        },

        _onHeroTouchEnd: function (event) {
            var touch = event.originalEvent.changedTouches[0];
            var distanceX = touch.clientX - this.heroTouchX;
            var distanceY = touch.clientY - this.heroTouchY;
            if (Math.abs(distanceX) > 48 && Math.abs(distanceX) > Math.abs(distanceY)) {
                this._showHero(this.heroIndex + (distanceX < 0 ? 1 : -1));
            }
            this._resumeHero();
        },

        _pauseHero: function () {
            window.clearInterval(this.heroTimer);
            if (this.hero) {
                this.hero.classList.add('is-paused');
            }
        },

        _resumeHero: function () {
            if (this.hero) {
                this.hero.classList.remove('is-paused');
            }
            this._startHero();
        },

        _initReveal: function () {
            if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                return;
            }
            var items = this.el.querySelectorAll('.ges-section-heading, .ges-solution-panel, .ges-sign, .ges-project-card, .ges-material-tile, .ges-values-grid article, .ges-home-story__copy, .ges-story-image, .ges-capability-showcase');
            if (!items.length) {
                return;
            }
            Array.prototype.forEach.call(items, function (item) {
                item.classList.add('ges-reveal');
            });
            this.revealObserver = new IntersectionObserver(function (entries, observer) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-visible');
                        observer.unobserve(entry.target);
                    }
                });
            }, {threshold: 0.16});
            Array.prototype.forEach.call(items, function (item) {
                this.revealObserver.observe(item);
            }.bind(this));
        },

        _initSolutionFilter: function () {
            var hash = window.location.hash.replace('#', '');
            if (['producao', 'operacao', 'execucao'].indexOf(hash) !== -1) {
                this._filterSolutions(hash);
            }
        },

        _onSolutionFilter: function (event) {
            this._filterSolutions(event.currentTarget.getAttribute('data-ges-solution-filter'));
        },

        _filterSolutions: function (filter) {
            var groups = this.el.querySelectorAll('[data-ges-solution-group]');
            var buttons = this.el.querySelectorAll('[data-ges-solution-filter]');
            Array.prototype.forEach.call(groups, function (group) {
                var visible = filter === 'all' || group.getAttribute('data-ges-solution-group') === filter;
                group.classList.toggle('is-filtered-out', !visible);
                group.setAttribute('aria-hidden', visible ? 'false' : 'true');
            });
            Array.prototype.forEach.call(buttons, function (button) {
                var active = button.getAttribute('data-ges-solution-filter') === filter;
                button.classList.toggle('is-active', active);
                button.setAttribute('aria-pressed', active ? 'true' : 'false');
            });
        },

        _onCapabilityChange: function (event) {
            this._showCapability(event.currentTarget.getAttribute('data-ges-capability'));
        },

        _showCapability: function (capability) {
            var buttons = this.el.querySelectorAll('[data-ges-capability]');
            var scenes = this.el.querySelectorAll('[data-ges-capability-scene]');
            Array.prototype.forEach.call(buttons, function (button) {
                var active = button.getAttribute('data-ges-capability') === capability;
                button.classList.toggle('is-active', active);
                button.setAttribute('aria-pressed', active ? 'true' : 'false');
            });
            Array.prototype.forEach.call(scenes, function (scene) {
                var active = scene.getAttribute('data-ges-capability-scene') === capability;
                scene.classList.toggle('is-active', active);
                scene.setAttribute('aria-hidden', active ? 'false' : 'true');
                var image = scene.querySelector('[data-ges-src]');
                if (active && image) {
                    if (image.getAttribute('data-ges-srcset')) {
                        image.setAttribute('srcset', image.getAttribute('data-ges-srcset'));
                        image.removeAttribute('data-ges-srcset');
                    }
                    image.setAttribute('src', image.getAttribute('data-ges-src'));
                    image.removeAttribute('data-ges-src');
                }
                var link = scene.querySelector('a');
                if (link) {
                    link.setAttribute('tabindex', active ? '0' : '-1');
                }
            });
        },

        _onParallaxMove: function (event) {
            if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                return;
            }
            var rect = event.currentTarget.getBoundingClientRect();
            var x = ((event.clientX - rect.left) / rect.width - 0.5) * 18;
            var y = ((event.clientY - rect.top) / rect.height - 0.5) * 18;
            event.currentTarget.style.setProperty('--ges-x', x.toFixed(2) + 'px');
            event.currentTarget.style.setProperty('--ges-y', y.toFixed(2) + 'px');
            event.currentTarget.style.setProperty('--ges-x-inverse', (-x * 0.7).toFixed(2) + 'px');
            event.currentTarget.style.setProperty('--ges-y-inverse', (-y * 0.7).toFixed(2) + 'px');
        },

        _onParallaxLeave: function (event) {
            ['--ges-x', '--ges-y', '--ges-x-inverse', '--ges-y-inverse'].forEach(function (property) {
                event.currentTarget.style.setProperty(property, '0px');
            });
        },

        _initCounters: function () {
            var counters = this.el.querySelectorAll('[data-ges-count]');
            if (!counters.length) {
                return;
            }
            var animate = function (counter) {
                var target = parseInt(counter.getAttribute('data-ges-count'), 10);
                var pad = parseInt(counter.getAttribute('data-ges-pad') || '0', 10);
                var start = performance.now();
                var duration = 1100;
                var frame = function (now) {
                    var progress = Math.min((now - start) / duration, 1);
                    var eased = 1 - Math.pow(1 - progress, 3);
                    var value = Math.round(target * eased);
                    var formatted = String(value).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
                    counter.textContent = pad ? formatted.padStart(pad, '0') : formatted;
                    if (progress < 1) {
                        window.requestAnimationFrame(frame);
                    }
                };
                window.requestAnimationFrame(frame);
            };
            if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                Array.prototype.forEach.call(counters, function (counter) {
                    var value = counter.getAttribute('data-ges-count');
                    counter.textContent = value.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
                });
                return;
            }
            this.counterObserver = new IntersectionObserver(function (entries, observer) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        animate(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            }, {threshold: 0.65});
            Array.prototype.forEach.call(counters, function (counter) {
                counter.textContent = counter.getAttribute('data-ges-pad') ? '00' : '0';
                this.counterObserver.observe(counter);
            }.bind(this));
        },

        _initLazyBackgrounds: function () {
            var items = this.el.querySelectorAll('[data-ges-lazy-bg]');
            var load = function (item) {
                item.style.backgroundImage = "url('" + item.getAttribute('data-ges-lazy-bg') + "')";
                item.removeAttribute('data-ges-lazy-bg');
            };
            if (!('IntersectionObserver' in window)) {
                Array.prototype.forEach.call(items, load);
                return;
            }
            this.lazyBackgroundObserver = new IntersectionObserver(function (entries, observer) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        load(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            }, {rootMargin: '320px 0px'});
            Array.prototype.forEach.call(items, function (item) {
                this.lazyBackgroundObserver.observe(item);
            }.bind(this));
        },
    });

    publicWidget.registry.GesCatalog = publicWidget.Widget.extend({
        selector: '[data-ges-catalog]',
        events: {
            'click [data-catalog-filter]': '_onFilterClick',
            'input [data-catalog-search]': '_onSearch',
            'click [data-catalog-compare]': '_onCompareClick',
        },

        start: function () {
            this.activeFilter = 'all';
            this.compareItems = [];
            this._applyQuerySearch();
            this._applyFilters();
            this._updateCompareTray();
            return this._super.apply(this, arguments);
        },

        _items: function () {
            return this.el.querySelectorAll('[data-catalog-item]');
        },

        _normalize: function (value) {
            return String(value || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        },

        _applyQuerySearch: function () {
            var field = this.el.querySelector('[data-catalog-search]');
            if (!field || !window.URLSearchParams) {
                return;
            }
            var query = new URLSearchParams(window.location.search).get('search');
            if (query) {
                field.value = query.slice(0, 80);
            }
        },

        _onFilterClick: function (ev) {
            var button = ev.currentTarget;
            this.activeFilter = button.getAttribute('data-catalog-filter') || 'all';
            Array.prototype.forEach.call(this.el.querySelectorAll('[data-catalog-filter]'), function (filterButton) {
                var isActive = filterButton === button;
                filterButton.classList.toggle('is-active', isActive);
                filterButton.setAttribute('aria-pressed', isActive ? 'true' : 'false');
            });
            this._highlightMap();
            this._applyFilters();
        },

        _onSearch: function () {
            this._applyFilters();
        },

        _applyFilters: function () {
            var queryField = this.el.querySelector('[data-catalog-search]');
            var query = this._normalize(queryField && queryField.value);
            var visible = 0;
            Array.prototype.forEach.call(this._items(), function (item) {
                var group = item.getAttribute('data-catalog-item');
                var text = this._normalize(item.getAttribute('data-catalog-text'));
                var matchesFilter = this.activeFilter === 'all' || group === this.activeFilter;
                var matchesSearch = !query || text.indexOf(query) !== -1;
                var show = matchesFilter && matchesSearch;
                item.classList.toggle('is-hidden', !show);
                if (show) {
                    visible += 1;
                }
            }.bind(this));
            var empty = this.el.querySelector('[data-catalog-empty]');
            if (empty) {
                empty.hidden = visible !== 0;
            }
            this._highlightMap();
        },

        _highlightMap: function () {
            Array.prototype.forEach.call(this.el.querySelectorAll('[data-catalog-map]'), function (mapItem) {
                var key = mapItem.getAttribute('data-catalog-map');
                mapItem.classList.toggle('is-active', this.activeFilter === 'all' || key === this.activeFilter);
            }.bind(this));
        },

        _onCompareClick: function (ev) {
            var button = ev.currentTarget;
            var name = button.getAttribute('data-catalog-name');
            var index = this.compareItems.indexOf(name);
            if (index === -1) {
                if (this.compareItems.length >= 4) {
                    this.compareItems.shift();
                    var selected = this.el.querySelector('[data-catalog-compare].is-active');
                    if (selected) {
                        selected.classList.remove('is-active');
                        selected.setAttribute('aria-pressed', 'false');
                    }
                }
                this.compareItems.push(name);
                button.classList.add('is-active');
                button.setAttribute('aria-pressed', 'true');
            } else {
                this.compareItems.splice(index, 1);
                button.classList.remove('is-active');
                button.setAttribute('aria-pressed', 'false');
            }
            this._updateCompareTray();
        },

        _updateCompareTray: function () {
            var count = this.el.querySelector('[data-catalog-count]');
            var list = this.el.querySelector('[data-catalog-list]');
            var total = this.compareItems.length;
            if (count) {
                count.textContent = total + (total === 1 ? ' item' : ' itens');
            }
            if (list) {
                list.textContent = total ? this.compareItems.join(' • ') : 'Seleccione produtos para comparar capacidades antes de pedir cotação.';
            }
        },
    });

    publicWidget.registry.GesPublicTools = publicWidget.Widget.extend({
        selector: '[data-ges-tools]',
        events: {
            'input [data-tool-field]': '_updateTools',
            'change [data-tool-field]': '_updateTools',
            'change [data-readiness-item]': '_updateReadiness',
        },

        start: function () {
            this._updateTools();
            this._updateReadiness();
            return this._super.apply(this, arguments);
        },

        _field: function (tool, name) {
            return tool.querySelector('[data-tool-field="' + name + '"]');
        },

        _number: function (tool, name) {
            var field = this._field(tool, name);
            return Math.max(0, parseFloat(field && field.value ? String(field.value).replace(',', '.') : '0') || 0);
        },

        _value: function (tool, name) {
            var field = this._field(tool, name);
            return field ? field.value : '';
        },

        _formatDecimal: function (value, digits) {
            return value.toLocaleString('pt-PT', {minimumFractionDigits: digits, maximumFractionDigits: digits});
        },

        _setOutput: function (name, value, note) {
            var output = this.el.querySelector('[data-tool-output="' + name + '"]');
            var noteEl = this.el.querySelector('[data-tool-note="' + name + '"]');
            if (output) {
                output.textContent = value;
            }
            if (noteEl && note) {
                noteEl.textContent = note;
            }
        },

        _updateTools: function () {
            this._updateConcrete();
            this._updateBlocks();
            this._updateTransport();
            this._updateAdvisor();
        },

        _updateConcrete: function () {
            var tool = this.el.querySelector('[data-ges-tool="concrete"]');
            if (!tool) { return; }
            var volume = this._number(tool, 'length') * this._number(tool, 'width') * (this._number(tool, 'depth') / 100);
            volume = volume * (1 + this._number(tool, 'waste') / 100);
            this._setOutput('concrete', this._formatDecimal(volume, 2) + ' m³');
        },

        _updateBlocks: function () {
            var tool = this.el.querySelector('[data-ges-tool="blocks"]');
            if (!tool) { return; }
            var area = this._number(tool, 'wall_length') * this._number(tool, 'wall_height');
            var blockArea = this._number(tool, 'block_area') || 0.08;
            var units = Math.ceil((area / blockArea) * (1 + this._number(tool, 'waste') / 100));
            this._setOutput('blocks', units.toLocaleString('pt-PT') + ' un.');
        },

        _updateTransport: function () {
            var tool = this.el.querySelector('[data-ges-tool="transport"]');
            if (!tool) { return; }
            var load = this._number(tool, 'load');
            var capacity = this._number(tool, 'capacity') || 1;
            var distance = this._number(tool, 'distance');
            var urgency = this._value(tool, 'urgency');
            var trips = Math.ceil(load / capacity);
            var note = distance ? 'Percurso estimado: ' + this._formatDecimal(distance * Math.max(trips, 1) * 2, 0) + ' km operacionais.' : 'Informe distância para prever esforço logístico.';
            if (urgency === 'urgent') {
                note = 'Prioridade alta: confirme disponibilidade de frota com a GES. ' + note;
            }
            this._setOutput('transport', trips.toLocaleString('pt-PT') + (trips === 1 ? ' viagem' : ' viagens'), note);
        },

        _updateReadiness: function () {
            var items = this.el.querySelectorAll('[data-readiness-item]');
            var checked = 0;
            Array.prototype.forEach.call(items, function (item) {
                if (item.checked) { checked += 1; }
            });
            var percent = items.length ? Math.round((checked / items.length) * 100) : 0;
            var note = percent >= 80 ? 'Projecto bem preparado para cotação.' : (percent >= 40 ? 'Faltam dados importantes para acelerar a resposta.' : 'Reúna medições, localização e prazo para uma cotação mais rápida.');
            this._setOutput('readiness', percent + '%', note);
        },

        _updateAdvisor: function () {
            var tool = this.el.querySelector('[data-ges-tool="advisor"]');
            if (!tool) { return; }
            var need = this._value(tool, 'need');
            var phase = this._value(tool, 'phase');
            var speed = this._value(tool, 'speed');
            var scale = this._value(tool, 'scale');
            var recommendation = 'Produção + Comercial';
            if (need === 'materials') {
                recommendation = 'Betão, blocos, vigotas e ferro';
            } else if (need === 'equipment') {
                recommendation = 'Aluguer de equipamentos + transporte';
            } else if (need === 'execution') {
                recommendation = 'Mão de obra + estaleiros';
            } else if (need === 'logistics') {
                recommendation = 'Transporte + armazém e logística';
            } else if (need === 'integrated') {
                recommendation = 'Produção + logística + execução';
            }
            if (scale === 'large' || speed === 'critical') {
                recommendation += ' + coordenação técnica';
            }
            var note = phase === 'planning' ? 'Ideal para iniciar conversa técnica e validar quantidades.' : 'Ideal para validar disponibilidade, prazo e condições comerciais.';
            this._setOutput('advisor', recommendation, note);
        },
    });

    publicWidget.registry.GesPortalCalculator = publicWidget.Widget.extend({
        selector: '[data-ges-portal-calculator]',
        events: {
            'input [data-ges-product-qty]': '_updateSummary',
            'input [data-calc-field]': '_onCalculatorInput',
            'change [data-calc-field]': '_onCalculatorInput',
            'click [data-calc-apply]': '_onCalculatorApply',
        },

        start: function () {
            this.currency = this.el.getAttribute('data-ges-currency') || '';
            this._updateAllResults();
            this._updateSummary();
            return this._super.apply(this, arguments);
        },

        _number: function (element) {
            return Math.max(0, parseFloat(element && element.value ? element.value.replace(',', '.') : '0') || 0);
        },

        _calculate: function (type) {
            var tool = this.el.querySelector('[data-ges-calc="' + type + '"]');
            if (!tool) {
                return 0;
            }
            var value = function (name) {
                return this._number(tool.querySelector('[data-calc-field="' + name + '"]'));
            }.bind(this);
            var waste = 1 + value('waste') / 100;
            if (type === 'concrete') {
                return value('length') * value('width') * (value('depth') / 100) * waste;
            }
            if (type === 'blocks') {
                var blockArea = value('block_size') || 0.08;
                return Math.ceil((value('wall_length') * value('wall_height') / blockArea) * waste);
            }
            return 0;
        },

        _formatQuantity: function (type, value) {
            if (type === 'blocks') {
                return Math.ceil(value).toLocaleString('pt-PT') + ' un.';
            }
            return value.toLocaleString('pt-PT', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' m³';
        },

        _onCalculatorInput: function (event) {
            var tool = event.currentTarget.closest('[data-ges-calc]');
            if (tool) {
                this._updateResult(tool.getAttribute('data-ges-calc'));
            }
        },

        _updateResult: function (type) {
            var output = this.el.querySelector('[data-calc-result="' + type + '"]');
            if (output) {
                output.textContent = this._formatQuantity(type, this._calculate(type));
            }
        },

        _updateAllResults: function () {
            Array.prototype.forEach.call(this.el.querySelectorAll('[data-ges-calc]'), function (tool) {
                this._updateResult(tool.getAttribute('data-ges-calc'));
            }.bind(this));
        },

        _onCalculatorApply: function (event) {
            var type = event.currentTarget.getAttribute('data-calc-apply');
            var quantity = this._calculate(type);
            var card = this.el.querySelector('[data-product-kind="' + type + '"]');
            var input = card && card.querySelector('[data-ges-product-qty]');
            if (!input || quantity <= 0) {
                return;
            }
            input.value = type === 'blocks' ? Math.ceil(quantity) : quantity.toFixed(2);
            card.classList.add('is-selected');
            input.focus();
            this._updateSummary();
        },

        _updateSummary: function () {
            var count = 0;
            var total = 0;
            var hasPriceOnRequest = false;
            Array.prototype.forEach.call(this.el.querySelectorAll('.ges-material-card'), function (card) {
                var input = card.querySelector('[data-ges-product-qty]');
                var quantity = this._number(input);
                var price = parseFloat(card.getAttribute('data-product-price') || '0') || 0;
                var selected = quantity > 0;
                card.classList.toggle('is-selected', selected);
                if (selected) {
                    count += 1;
                    total += quantity * price;
                    hasPriceOnRequest = hasPriceOnRequest || price <= 0;
                }
            }.bind(this));
            var counter = this.el.querySelector('[data-ges-item-count]');
            var totalElement = this.el.querySelector('[data-ges-estimated-total]');
            if (counter) {
                counter.textContent = count;
            }
            if (totalElement) {
                if (!count) {
                    totalElement.textContent = '—';
                } else {
                    var formatted = total.toLocaleString('pt-PT', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                    totalElement.textContent = total > 0 ? formatted + ' ' + this.currency + (hasPriceOnRequest ? ' + itens sob consulta' : '') : 'Preço sob consulta';
                }
            }
        },
    });
});
