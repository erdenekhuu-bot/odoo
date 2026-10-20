
import json
from odoo import http
from odoo.http import request


class APIController(http.Controller):

    @http.route('/game/members/login',type='http',auth='public',methods=['POST'],csrf=False
    )
    def login(self, **kw):
        try:
            data = json.loads(request.httprequest.get_data(as_text=True))
            name = data.get('name')
            if not isinstance(name, str) or not name.strip():
                return request.make_json_response(
                    {"error": "Name is required"},
                    status=400
                )

            member = request.env['game.member'].sudo().search([
                ('name', '=', name.strip()),
            ], limit=1)

            if not member:
                return request.make_json_response(
                    {"error": "Member not found"},
                    status=404
                )

            return request.make_json_response({
                "success": True,
                "id": member.id,
                "name": member.name,
                "score": member.score
            }, status=200)

        except (ValueError, TypeError):
            return request.make_json_response(
                {"error": "Invalid member data"},
                status=400
            )


    @http.route('/game/members', type='http',auth='public', methods=['GET'])
    def get_members(self, **kwargs):
        members = request.env['game.member'].sudo().search([], limit=10, order='id asc')

        return request.make_json_response({"success": True,"data": members.read(['name', 'phone', 'score'])})

    @http.route('/game/members/<int:member_id>',type='http', auth='public', methods=['GET'])
    def get_member(self, member_id):
        member = request.env['game.member'].sudo().browse(member_id).exists()
        if not member:
            return request.make_json_response({"error": "Member not found"}, status=404)

        return request.make_json_response({
            "success": True,
            "data": member.read(['name', 'phone', 'score'])[0]
        })

    # CREATE
    @http.route('/game/members', type='http',auth='public', methods=['POST'], csrf=False)
    def create_member(self, **kwargs):
        try:
            data = json.loads(request.httprequest.get_data(as_text=True))

            if not isinstance(data, dict):
                raise ValueError()

            name = data.get('name')
            phone = data.get('phone')
            score = data.get('score')

            if (not isinstance(name, str) or not name.strip()
                    or not isinstance(phone, str) or not phone.strip()
                    or type(score) is not int):
                raise ValueError()

        except (ValueError, UnicodeDecodeError):
            return request.make_json_response(
                {"error": "Invalid member data"}, status=400
            )

        member = request.env['game.member'].sudo().create({
            'name': name,
            'phone': phone,
            'score': score
        })

        return request.make_json_response({
            "success": True,
            "id": member.id
        }, status=201)

    # DELETE
    @http.route('/game/members/<int:member_id>',
                type='http', auth='public',
                methods=['DELETE'], csrf=False)
    def delete_member(self, member_id):

        member = request.env['game.member'].sudo().browse(member_id).exists()
        if not member:
            return request.make_json_response({"error": "Member not found"}, status=404)

        member.unlink()

        return request.make_json_response({
            "success": True,
            "message": "Member deleted"
        })
