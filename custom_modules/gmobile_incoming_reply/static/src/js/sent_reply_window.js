/** @odoo-module **/

import { registry } from "@web/core/registry";

console.log("===== GMOBILE REPLY JS LOADED =====");

function gmobileReplySuccess(env, action) {
    console.log("===== GMOBILE REPLY ACTION CALLED =====", action);

    const params = action.params || {};

    env.services.notification.add(
        params.message || "Хариу амжилттай илгээгдлээ.",
        {
            title: params.title || "Амжилттай",
            type: "success",
            sticky: false,
        }
    );
}

registry.category("actions").add(
    "display_notification",
    gmobileReplySuccess
);

console.log("===== GMOBILE REPLY ACTION REGISTERED =====");