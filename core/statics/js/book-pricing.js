(function () {
    var forms = document.querySelectorAll('[data-book-pricing-form]');
    var priceFieldNames = [
        'credit_cost_for_7_days',
        'credit_cost_for_14_days',
        'credit_cost_for_20_days',
        'credit_cost_for_30_days'
    ];

    forms.forEach(function (form) {
        var statusField = form.querySelector('[name="status"]');
        var priceFields = priceFieldNames
            .map(function (name) {
                return form.querySelector('[name="' + name + '"]');
            })
            .filter(function (field) {
                return Boolean(field);
            });
        var paidOnlyBlocks = form.querySelectorAll('[data-paid-only]');

        if (!statusField) {
            return;
        }

        var togglePaidFields = function () {
            var isPaid = statusField.value === 'paid';

            paidOnlyBlocks.forEach(function (block) {
                block.hidden = !isPaid;
            });

            priceFields.forEach(function (field) {
                field.required = isPaid;
            });
        };

        statusField.addEventListener('change', togglePaidFields);
        togglePaidFields();
    });
})();
