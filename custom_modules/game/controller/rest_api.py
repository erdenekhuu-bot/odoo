
import json
from odoo import http
from odoo.http import request


class APIController(http.Controller):

    @http.route(
        '/game/members/login',type='http',auth='public',methods=['POST'],csrf=False,cors='*')
    def login(self, **kw):
        try:
            data = json.loads(request.httprequest.get_data(as_text=True))
            name = data.get('name')
            phone = data.get('phone', '')

            if not isinstance(name, str) or not name.strip():
                return request.make_json_response(
                    {"error": "Name is required"},
                    status=400
                )

            name = name.strip()
            Model = request.env['game.member'].sudo()
            member = Model.search([('name', '=', name)], limit=1)

            # Байвал 200 буцаана
            if member:
                return request.make_json_response({
                    "success": True,
                    "id": member.id,
                    "name": member.name,
                    "score": member.score
                }, status=200)

            # Байхгүй бол create хийнэ
            if not isinstance(phone, str):
                phone = ''

            member = Model.create({
                'name': name,
                'phone': phone.strip(),
                'score': 0
            })

            return request.make_json_response({
                "success": True,
                "id": member.id,
                "name": member.name,
                "score": member.score
            }, status=201)

        except (ValueError, TypeError, AttributeError):
            return request.make_json_response(
                {"error": "Invalid member data"},
                status=400
            )


    @http.route('/game/members', type='http',auth='public', methods=['GET'],cors='*')
    def get_members(self, **kwargs):
        members = request.env['game.member'].sudo().search([], limit=10, order='score desc')

        return request.make_json_response({"success": True,"data": members.read(['name', 'phone', 'score'])})

    # Update
    @http.route(
        '/game/members/<int:member_id>',
        type='http',
        auth='public',
        methods=['GET', 'PATCH', 'DELETE'],
        csrf=False,
        cors='*'
    )
    def member_detail(self, member_id, **kwargs):

        member = request.env['game.member'].sudo().browse(member_id).exists()

        if not member:
            return request.make_json_response(
                {"error": "Member not found"},
                status=404
            )

        method = request.httprequest.method

        # GET
        if method == 'GET':
            return request.make_json_response({
                "success": True,
                "data": member.read(['name', 'phone', 'score'])[0]
            })

        # PATCH
        if method == 'PATCH':
            try:
                data = json.loads(
                    request.httprequest.get_data(as_text=True)
                )

                vals = {}
                if 'score' in data:
                    vals['score'] = int(data['score'])

                member.write(vals)

                return request.make_json_response({
                    "status": "success"
                })

            except (ValueError, TypeError):
                return request.make_json_response(
                    {"error": "Invalid data"},
                    status=400
                )

        # DELETE
        if method == 'DELETE':
            member.unlink()

            return request.make_json_response({
                "success": True,
                "message": "Member deleted"
            })

