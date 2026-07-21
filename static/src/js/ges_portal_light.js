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
}());
