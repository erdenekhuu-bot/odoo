/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class GMobileInvoiceDashboard extends Component {
    static template = "gmobile_invoice.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            items: [],
            total: 0,
            error: null,
        });

        onWillStart(async () => {
            try {
                const result = await this.orm.call(
                    "gmobile.invoice.service",
                    "fetch_items",
                    []
                );
                this.state.items = result.items || [];
                this.state.total = result.total || 0;
            } catch (e) {
                this.state.error = "Дата авч чадсангүй";
                console.error(e);
            } finally {
                this.state.loading = false;
            }
        });
    }
}

registry.category("actions").add("gmobile_invoice.dashboard", GMobileInvoiceDashboard);
