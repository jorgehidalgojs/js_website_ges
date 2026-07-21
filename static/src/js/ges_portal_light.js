(function () {
    'use strict';

    function ready(callback) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', callback, {once: true});
        } else {
            callback();
        }
    }

    ready(function () {
        var root = document.querySelector('[data-ges-portal-calculator]');
        if (!root) {
            return;
        }

        var currency = root.getAttribute('data-ges-currency') || '';
        var number = function (element) {
            return Math.max(0, parseFloat(element && element.value ? element.value.replace(',', '.') : '0') || 0);
        };
        var calculate = function (type) {
            var tool = root.querySelector('[data-ges-calc="' + type + '"]');
            if (!tool) { return 0; }
            var value = function (name) { return number(tool.querySelector('[data-calc-field="' + name + '"]')); };
            var waste = 1 + value('waste') / 100;
            if (type === 'concrete') {
                return value('length') * value('width') * (value('depth') / 100) * waste;
            }
            if (type === 'blocks') {
                return Math.ceil((value('wall_length') * value('wall_height') / (value('block_size') || 0.08)) * waste);
            }
            return 0;
        };
        var updateResult = function (type) {
            var output = root.querySelector('[data-calc-result="' + type + '"]');
            var value = calculate(type);
            if (output) {
                output.textContent = type === 'blocks'
                    ? Math.ceil(value).toLocaleString('pt-PT') + ' un.'
                    : value.toLocaleString('pt-PT', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' m³';
            }
        };
        var updateSummary = function () {
            var count = 0;
            var total = 0;
            var consultation = false;
            root.querySelectorAll('.ges-material-card').forEach(function (card) {
                var quantity = number(card.querySelector('[data-ges-product-qty]'));
                var price = parseFloat(card.getAttribute('data-product-price') || '0') || 0;
                card.classList.toggle('is-selected', quantity > 0);
                if (quantity > 0) {
                    count += 1;
                    total += quantity * price;
                    consultation = consultation || price <= 0;
                }
            });
            var counter = root.querySelector('[data-ges-item-count]');
            var totalElement = root.querySelector('[data-ges-estimated-total]');
            if (counter) { counter.textContent = count; }
            if (totalElement) {
                var formatted = total.toLocaleString('pt-PT', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                totalElement.textContent = !count ? '—' : (total > 0 ? formatted + ' ' + currency + (consultation ? ' + itens sob consulta' : '') : 'Preço sob consulta');
            }
        };

        root.querySelectorAll('[data-ges-calc]').forEach(function (tool) { updateResult(tool.getAttribute('data-ges-calc')); });
        updateSummary();
        root.addEventListener('input', function (event) {
            if (event.target.matches('[data-calc-field]')) {
                updateResult(event.target.closest('[data-ges-calc]').getAttribute('data-ges-calc'));
            }
            if (event.target.matches('[data-ges-product-qty]')) { updateSummary(); }
        }, {passive: true});
        root.addEventListener('change', function (event) {
            if (event.target.matches('[data-calc-field]')) {
                updateResult(event.target.closest('[data-ges-calc]').getAttribute('data-ges-calc'));
            }
        });
        root.addEventListener('click', function (event) {
            var button = event.target.closest('[data-calc-apply]');
            if (!button) { return; }
            var type = button.getAttribute('data-calc-apply');
            var quantity = calculate(type);
            var card = root.querySelector('[data-product-kind="' + type + '"]');
            var input = card && card.querySelector('[data-ges-product-qty]');
            if (input && quantity > 0) {
                input.value = type === 'blocks' ? Math.ceil(quantity) : quantity.toFixed(2);
                updateSummary();
                input.focus({preventScroll: true});
            }
        });
    });

    ready(function () {
        var form = document.querySelector('[data-ges-subcontractor-register]');
        if (!form) {
            return;
        }

        var supplierType = form.querySelector('[data-ges-supplier-type]');
        var companyLabel = form.querySelector('[data-ges-company-label]');
        var companyInput = companyLabel && companyLabel.querySelector('input');
        var companyOnlyFields = form.querySelectorAll('[data-ges-company-only]');
        var fiscalFields = form.querySelectorAll('[data-ges-fiscal-field]');

        function setLabelText(label, text) {
            if (!label) { return; }
            Array.prototype.slice.call(label.childNodes).some(function (node) {
                if (node.nodeType === Node.TEXT_NODE) {
                    node.nodeValue = text;
                    return true;
                }
                return false;
            });
        }

        function toggleFields(fields, visible) {
            fields.forEach(function (field) {
                field.classList.toggle('is-context-hidden', !visible);
                field.querySelectorAll('input, select, textarea').forEach(function (input) {
                    if (!visible) {
                        input.setAttribute('data-ges-disabled-context', '1');
                        input.disabled = true;
                    } else if (input.getAttribute('data-ges-disabled-context') === '1') {
                        input.disabled = false;
                        input.removeAttribute('data-ges-disabled-context');
                    }
                });
            });
        }

        function updateSupplierContext() {
            var value = supplierType ? supplierType.value : 'company';
            var isCompany = value === 'company';
            var isIndividual = value === 'individual';

            setLabelText(companyLabel, isIndividual ? 'Nome profissional *' : (isCompany ? 'Empresa *' : 'Nome da equipa *'));
            if (companyInput) {
                companyInput.placeholder = isIndividual ? 'Nome usado profissionalmente' : (isCompany ? 'Nome comercial da empresa' : 'Nome da equipa técnica');
            }
            toggleFields(companyOnlyFields, isCompany);
            toggleFields(fiscalFields, !isIndividual);
        }

        updateSupplierContext();
        if (supplierType) {
            supplierType.addEventListener('change', updateSupplierContext);
        }
    });
}());
