/** @odoo-module **/

import { registry } from "@web/core/registry";

async function gmobileReplySuccess(env, action) {
    const notification = env.services.notification;

    const params = action.params || {};

    notification.add(
        params.message || "Хариу амжилттай илгээгдлээ.",
        {
            title: params.title || "Хариу",
            type: "success",
            sticky: false,
        }
    );
}

registry.category("actions").add(
    "gmobile_reply_success",
    gmobileReplySuccess
);