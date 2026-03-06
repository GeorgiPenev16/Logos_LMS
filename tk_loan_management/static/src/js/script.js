/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

$(document).ready(function () {

    $('#installment_type').on('change', function (e) {
        const link = $(this).val();
        if (link){
        let value;
            if(link === 'monthly') value = 'Months'
            else if(link === 'quarterly') value = 'Quarters'
            else if(link === 'yearly') value = 'Years'
             $('#select-requested-term').val(value)
             $('#select-requested-term').removeClass('d-none')
        } else {
            $('#select-requested-term').addClass('d-none')
        }
    });

    $('#loan_type').on('change', function () {
        let value = $(this).val()
        if (value){
            rpc('/get-loan-type-details', {
                'loan_type': value,
        }).then(function (values) {
            let documentDetails = $('#document-details');
            documentDetails.empty();
            values.documents.forEach(function(doc) {
                let documentsRow = `
                            <tr>
                                <td class="cus-value" style="font-size: 0.9rem;">
                                    ${doc.name}
                                </td>
                                <td>
                                    <input type="file" class="docs-style" name="${doc.name}" id="${doc.name}"
                                           accept="image/*,.pdf" required="required"/>
                                </td>
                            </tr>
                        `;
                        $('#document-details').append(documentsRow);
            });

            if (values.tc) {
                $('#terms-conditions-tab-li').removeClass('d-none')
                $('#terms-conditions-tab-pane').empty().append(`<span>${values.tc}</span>`);
            } else {
                $('#terms-conditions-tab-li').addClass('d-none')
            }

            if (values.rpt) {
                $('#repayment-terms-tab-li').removeClass('d-none')
                $('#repayment-terms-tab-pane').empty().append(`<span>${values.rpt}</span>`);
            } else {
                $('#repayment-terms-tab-li').addClass('d-none')
            }


        });}
        else{
            let documentDetails = $('#document-details');
            documentDetails.empty();
        }
    });


    $('#term').on('change', function () {
        if ($(this).val() <= 0){
            $(this).val(1)
        }
    });

    $('#loan_amount').on('change', function () {
        if ($(this).val() <= 0){
            $(this).val(1)
        }
    });


    $('#terms_and_condition_checked,#repayment_terms_checked').on('change', function (e) {
        e.preventDefault();
        const link = $('#term_check');
        if ($('#terms_and_condition_checked').is(':checked') && $('#repayment_terms_checked').is(':checked')) {
            link.attr('data-bs-toggle', 'modal');
            link.attr('data-bs-target', '#loanSignAccept');
            // Remove the disabled class
            link.removeClass('disabled');
        } else {
            // Remove modal attributes
            link.removeAttr('data-bs-toggle');
            link.removeAttr('data-bs-target');
            // Add the disabled class
            link.addClass('disabled');
        }
    });

    $('#reject-loan-form').on('submit', function (event) {
        let reason = $('#cst_loan_reject_reason').val()
        let alertEle = $('#validation-error')

        alertEle.addClass('d-none')
        if (!reason) {
            event.preventDefault()
            alertEle.text('Please enter reason!')
            alertEle.removeClass('d-none')
        }
    });

    $('#loanRequestForm').on('submit', function (event) {
        let fullname = $('#full_name').val()
        let email = $('#email_address').val()
        let phone = $('#customer_phone').val()
        let loanType = $('#loan_type').val()
        let loanAmount = $('#loan_amount').val()
        let purpose = $('#purpose').val()
        let isDocumentUpload = true

        let documents = $('.docs-style').each((index,element)=>{
            if (!element.files) {
                isDocumentUpload = false
            }
        })
        let alertEle = $('#validation-error')

        alertEle.addClass('d-none')
        if (!fullname) {
            event.preventDefault()
            alertEle.text('Please enter full name!')
            alertEle.removeClass('d-none')
        }
        else if (!email) {
            event.preventDefault()
            alertEle.text('Please enter email address!')
            alertEle.removeClass('d-none')
        }
        else if (!phone) {
            event.preventDefault()
            alertEle.text('Please enter phone!')
            alertEle.removeClass('d-none')
        }
        else if (!loanType) {
            event.preventDefault()
            alertEle.text('Please enter loan type!')
            alertEle.removeClass('d-none')
        }
        else if (!loanAmount) {
            event.preventDefault()
            alertEle.text('Please enter loan amount!')
            alertEle.removeClass('d-none')
        }
        else if (!purpose) {
            event.preventDefault()
            alertEle.text('Please enter purpose!')
            alertEle.removeClass('d-none')
        }
        else if (!isDocumentUpload) {
            event.preventDefault()
            alertEle.text('Please upload document!')
            alertEle.removeClass('d-none')
        }
    });

    $('#uploadCollateral').on('submit', function (event) {
        let isCollateralUpload = true

        for (let i=0; i<$('.docs-style').length; i++){
        let element = $('.docs-style')[i]
            if ($('.docs-style')[i].files.length <= 0) {
                isCollateralUpload = false
                break
            }
        }

        let alertEle = $('#validation-error')
        alertEle.addClass('d-none')

        if (!isCollateralUpload) {
            event.preventDefault()
            alertEle.text('Please upload collateral!')
            alertEle.removeClass('d-none')
        }
    });

    $('#uploadDocument').on('submit', function (event) {
        let isDocumentUpload = true

        for (let i=0; i<$('.docs-style').length; i++){
        let element = $('.docs-style')[i]
            if ($('.docs-style')[i].files.length <= 0) {
                isDocumentUpload = false
                break
            }
        }

        let alertEle = $('#validation-error')
        alertEle.addClass('d-none')

        if (!isDocumentUpload) {
            event.preventDefault()
            alertEle.text('Please upload document!')
            alertEle.removeClass('d-none')
        }
    });

})
