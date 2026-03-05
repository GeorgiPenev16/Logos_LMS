/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { session } from "@web/session";
import { Domain } from "@web/core/domain";
import { sprintf } from "@web/core/utils/strings";

const { Component, useSubEnv, useState, onMounted, onWillStart, useRef } = owl;
import { loadJS, loadCSS } from "@web/core/assets"

class CustomerLoanDashboard extends Component {
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");

        this.state = useState({
            customerLoanStatus: {
                'draft_loans': 0,
                'dept_approval_loans': 0,
                'confirmation_loans': 0,
                'disbursement_loans': 0,
                'in_progress_loans': 0,
                'closure_loans': 0,
                'pre_closure_loans': 0,
                'settlement_loans': 0,
                'rejected_loans': 0,
                'cancelled_loans': 0,
                'overdue_installments_loans_counts': 0,
                'unpaid_penalties_loans_counts': 0,
            },
        });

        useSubEnv({
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
        });
        this.disbursedLoanAmountByMonth = useRef('disbursed_loan_by_month');
        this.mostSellingLoans = useRef('most_selling_loans');
        this.loanAmountDetails = useRef('loan_details');
        this.receivedChargeDetails = useRef('received_charge_graph');

        onWillStart(async () => {
            let customerLoanData = await this.orm.call('customer.loan.dashboard', 'get_customer_loan_dashboard', []);
            if (customerLoanData) {
                this.state.customerLoanStatus = customerLoanData;
                this.state.disbursedLoanAmountByMonth = { 'x-axis': customerLoanData['disbursed_loan_by_month'][0], 'y-axis': customerLoanData['disbursed_loan_by_month'][1] }
                this.state.mostSellingLoans = { 'x-axis': customerLoanData['most_selling_loans'][0], 'y-axis': customerLoanData['most_selling_loans'][1] }
                this.state.loanAmountDetails = { 'x-axis': customerLoanData['loan_details'][0], 'y-axis': customerLoanData['loan_details'][1] }
                this.state.receivedChargeDetails = { 'x-axis': customerLoanData['received_charges'][0], 'y-axis': customerLoanData['received_charges'][1] }
            }
        });
        onMounted(() => {
            this.renderMostSellingLoans(this.mostSellingLoans.el, this.state.mostSellingLoans);
            this.renderLoanDetails(this.loanAmountDetails.el, this.state.loanAmountDetails);
            this.renderReceivedChargesGraph(this.receivedChargeDetails.el, this.state.receivedChargeDetails);
            this.renderDisbursedLoanAmountByMonth();
        })
    }

    viewCustomerLoans(status) {
        let domain, context;
        let loan = this.getCustomerLoans(status);
        if (status === 'all') {
            domain = []
        } else {
            domain = [['status', '=', status]]
        }
        context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: loan,
            res_model: 'customer.loan',
            view_mode: 'kanban',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form'], [false, 'calendar'], [false, 'pivot'], [false, 'graph'], [false, 'activity']],
            target: 'current',
            context: context,
            domain: domain,
        });
    }

    viewOverdueInstallmentLoans() {
        let domain, context;
        domain = [['id', 'in', this.state.customerLoanStatus['overdue_installments_loans']]]

        context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: "Overdue Installments",
            res_model: 'customer.loan',
            view_mode: 'kanban',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form'], [false, 'calendar'], [false, 'pivot'], [false, 'graph'], [false, 'activity']],
            target: 'current',
            context: context,
            domain: domain,
        });
    }

    viewUnpaidPenaltiesLoans() {
        let domain, context;
        domain = [['id', 'in', this.state.customerLoanStatus['unpaid_penalties_loans']]]

        context = { 'create': false }
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: "Overdue Penalties",
            res_model: 'customer.loan',
            view_mode: 'kanban',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form'], [false, 'calendar'], [false, 'pivot'], [false, 'graph'], [false, 'activity']],
            target: 'current',
            context: context,
            domain: domain,
        });
    }

    getCustomerLoans(status) {
        let loan;
        if (status === 'draft') {
            loan = 'Draft'
        } else if (status === 'dept_approval') {
            loan = 'Department Approval'
        } else if (status === 'confirmation') {
            loan = 'Confirmation'
        } else if (status === 'disbursement') {
            loan = 'Disbursement'
        } else if (status === 'in_progress') {
            loan = 'In-Progress'
        } else if (status === 'closure') {
            loan = 'Closure'
        } else if (status === 'pre_closure') {
            loan = 'Pre-Closure'
        } else if (status === 'settlement') {
            loan = 'Settlement'
        } else if (status === 'rejected') {
            loan = 'Rejected'
        } else if (status === 'cancel') {
            loan = 'Cancelled'
        }
        return loan;
    }

    renderGraph(el, options) {
        const graphData = new ApexCharts(el, options);
        graphData.render();
    }

    renderMostSellingLoans(div, customerLoanData) {
        let root = am5.Root.new(div);
        let chartData = [];

        root.setThemes([
            am5themes_Animated.new(root)
        ]);

        let chart = root.container.children.push(am5percent.PieChart.new(root, {
            layout: root.verticalLayout,
            radius: am5.percent(80),
        }));

        let series = chart.series.push(am5percent.PieSeries.new(root, {
            alignLabels: false,
            calculateAggregates: true,
            valueField: "value",
            categoryField: "category"
        }));
        series.slices.template.setAll({
            strokeWidth: 2,
            stroke: am5.color(0xffffff),
            tooltipText: "{category}: {value}",
        });

        series.labels.template.setAll({
            textType: "circular",
            centerX: 0,
            centerY: 0,
        });
        for (let i = 0; i < customerLoanData['x-axis'].length; i++) {
            chartData.push({
                value: customerLoanData['y-axis'][i],
                category: customerLoanData['x-axis'][i],
            })
        }
        series.data.setAll(chartData);

        let legend = chart.children.push(am5.Legend.new(root, {
            centerX: am5.p50,
            x: am5.p50,
            marginTop: 15,
            marginBottom: 15
        }));

        legend.data.setAll(series.dataItems);
        series.appear(1000, 100);
    }

    renderLoanDetails(div, customerLoanData) {
        let root = am5.Root.new(div);

        let chartData = [];

        root.setThemes([
            am5themes_Animated.new(root)
        ]);

        let chart = root.container.children.push(am5percent.PieChart.new(root, {
            layout: root.verticalLayout,
            innerRadius: am5.percent(50),
        }));

        let series = chart.series.push(am5percent.PieSeries.new(root, {
            valueField: "value",
            categoryField: "category",
            alignLabels: false,
        }));

        series.labels.template.setAll({
            textType: "circular",
            centerX: 0,
            centerY: 0,
        });
        series.get("colors").set("colors", [
            am5.color("#a367dc"),
            am5.color("#6771dc"),
        ]);

        series.slices.template.set("tooltipText", "{category}: {value}");

        for (let i = 0; i < customerLoanData['x-axis'].length; i++) {
            chartData.push({
                value: customerLoanData['y-axis'][i],
                category: customerLoanData['x-axis'][i],
            })
        }
        series.data.setAll(chartData);

        let legend = chart.children.push(am5.Legend.new(root, {
            centerX: am5.percent(50),
            x: am5.percent(50),
            marginTop: 15,
            marginBottom: 15,
        }));

        legend.data.setAll(series.dataItems);
        series.appear(1000, 100);
    }

    renderDisbursedLoanAmountByMonth() {
        const options = {
            series: [{
                name: "Months",
                data: this.state.disbursedLoanAmountByMonth['y-axis']
            }],
            chart: {
                height: 350,
                type: 'bar',
                zoom: {
                    enabled: false
                }
            },
            dataLabels: {
                enabled: false
            },
            stroke: {
                curve: 'smooth'
            },
            title: {
                align: 'left'
            },
            grid: {
                row: {
                    opacity: 0.5
                },
            },
            xaxis: {
                categories: this.state.disbursedLoanAmountByMonth['x-axis'],
            },
        };
        this.renderGraph(this.disbursedLoanAmountByMonth.el, options);
    }

    renderReceivedChargesGraph(div, customerLoanData) {
        let root = am5.Root.new(div);

        let chartData = [];

        root.setThemes([
            am5themes_Animated.new(root)
        ]);

        let chart = root.container.children.push(am5percent.PieChart.new(root, {
          startAngle: 180,
          endAngle: 360,
          layout: root.verticalLayout,
          innerRadius: am5.percent(50)
        }));

        let series = chart.series.push(am5percent.PieSeries.new(root, {
          startAngle: 180,
          endAngle: 360,
          valueField: "value",
          categoryField: "category",
          alignLabels: false
        }));

        series.states.create("hidden", {
          startAngle: 180,
          endAngle: 180
        });

        series.slices.template.setAll({
          cornerRadius: 5
        });

        series.ticks.template.setAll({
          forceHidden: true
        });

        series.labels.template.setAll({
          text: "{category}",
          textType: "circular",
          inside: false,
          radius: 10
        });

        series.get("colors").set("colors", [
            am5.color("#cb54bc"),
            am5.color("#b657cb"),
        ]);

        series.slices.template.set("tooltipText", "{category}: {value}");

        for (let i = 0; i < customerLoanData['x-axis'].length; i++) {
            chartData.push({
                value: customerLoanData['y-axis'][i],
                category: customerLoanData['x-axis'][i],
            })
        }
        series.data.setAll(chartData);

        let legend = chart.children.push(am5.Legend.new(root, {
            centerX: am5.percent(50),
            x: am5.percent(50),
            marginTop: 15,
            marginBottom: 15,
        }));

        legend.data.setAll(series.dataItems);
        series.appear(1000, 100);
    }
}

CustomerLoanDashboard.template = "tk_loan_management.customer_loan_dashboard";
registry.category("actions").add("customer_loan_dashboard", CustomerLoanDashboard);