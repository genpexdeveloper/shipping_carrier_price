# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013 Camptocamp
#    Copyright 2009-2013 Akretion,
#    Author: Emmanuel Samyn, Raphaël Valyi, Sébastien Beau,
#            Benoît Guillot, Joel Grand-Guillaume
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import fields, orm,osv
import math

class stock_picking(osv.Model):
    _inherit = 'stock.picking'
    _columns = {
        'courier_company': fields.char('Courier Company'),
        'ship_rate': fields.float('Ship Rate'),
    }

class shipping_price(osv.Model):
	_name = "shipping.price"
	_description = "Shipping Price"
	_columns = {
		'courier_company':fields.char('Courier Company'),
		'to_pincode':fields.char("To PIN"),
		'from_pincode':fields.char("From PIN"),
		'rate_per_500':fields.float('Rate per 500gm'),
		'rate_per_add_500':fields.float('Rate per additional 500gm'),
		'cod_charges':fields.float('COD Charges'),
		'fuel_charges':fields.float('Fuel Charges'),
	}

class sale_order(osv.Model):
	_inherit = 'sale.order'
	def action_view_delivery(self, cr, uid, ids, context=None):
		mod_obj = self.pool.get('ir.model.data')
		act_obj = self.pool.get('ir.actions.act_window')
		shipping_price_pool = self.pool.get('shipping.price')
		stock_picking_obj  = self.pool.get('stock.picking')
		result = mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree_all')
		id = result and result[1] or False
		result = act_obj.read(cr, uid, [id], context=context)[0]
		#compute the number of delivery orders to display
		pick_ids = []
		for so in self.browse(cr, uid, ids, context=context):
			pick_ids += [picking.id for picking in so.picking_ids]
            
        #choose the view_mode accordingly
		if len(pick_ids) > 1:
			result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
		else:
			res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
			result['views'] = [(res and res[1] or False, 'form')]
			result['res_id'] = pick_ids and pick_ids[0] or False
		print "\n\n\n==========result======",result['res_id'],ids
		if result['res_id']:
			if ids:
				total_net_weight = 0.0
				company_ship_costing_list = []
				so_obj = self.browse(cr,uid,ids[0])
				to_pin = str(so_obj.partner_id.zip)
				from_pin = str(so_obj.warehouse_id.partner_id.zip)
				for line in so_obj.order_line:
					total_net_weight += (line.product_uom_qty * line.product_id.weight_net)
				print "\n\nfrom_pin==",from_pin,"to_pin==",to_pin , type(from_pin),type(to_pin),total_net_weight
				cr.execute("select id from shipping_price WHERE (to_pincode = %s) AND (from_pincode = %s)", (to_pin, from_pin))
				shipping_price_ids = cr.fetchall()
				shipping_price_ids_list=[i[0] for i in shipping_price_ids]
				ship_cost_dict = {}
				if shipping_price_ids_list:
					for shipping_price_id in shipping_price_ids_list:
						shipping_price_obj = shipping_price_pool.browse(cr,uid,shipping_price_id)
						total_net_weight_gm = total_net_weight * 1000
						ship_costing = 0.0
						if total_net_weight_gm >= 500:
							ship_costing += shipping_price_obj.rate_per_500
							total_net_weight_gm = total_net_weight_gm - 500
						extart_weight = int(math.ceil(total_net_weight_gm/500))
						print "\n\nextart_weight=",extart_weight
						ship_costing += (shipping_price_obj.rate_per_add_500 * extart_weight)
						fuel_charge = (ship_costing*50/100)
						ship_costing = ship_costing + fuel_charge
						if 'Cash On Delivery' in so_obj.note:
							ship_costing = ship_costing + shipping_price_obj.cod_charges
						company_ship_costing_list.append(ship_costing)
						ship_cost_dict[shipping_price_obj.id] = ship_costing
			print "\n\n=========company_ship_costing_list=",company_ship_costing_list
			if company_ship_costing_list:
				print "\n\n=========ship_cost_dict=",ship_cost_dict
				best_shipping_rate = min(company_ship_costing_list)
				for key,value in ship_cost_dict.items():
					if best_shipping_rate == value:
						print "\n\n\n\n\n\n====",key,value
						stock_picking_obj.write(cr,uid,result['res_id'],{'courier_company': shipping_price_obj.courier_company,'ship_rate':value})
						print "\n\n\n ======done======="
		return result
