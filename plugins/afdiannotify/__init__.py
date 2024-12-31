from pydantic import BaseModel, Field

from app.core.config import settings
from app.plugins import _PluginBase
from typing import Any, List, Dict, Tuple
from app.log import logger
from app.schemas import NotificationType

class SkuDetail(BaseModel):
    sku_id: str = Field(..., description="SKU 的 ID")
    count: int = Field(..., description="SKU 数量")
    name: str = Field(..., description="SKU 名称")
    album_id: str = Field("", description="相册ID，可能为空")
    pic: str = Field("", description="SKU 图片地址")


class Order(BaseModel):
    out_trade_no: str = Field(..., description="爱发电生成的订单号")
    custom_order_id: str = Field("", description="自定义订单号，如：Steam12345")
    user_id: str = Field(..., description="爱发电用户ID")
    user_private_id: str = Field("", description="每个用户唯一的ID，如微信 unionid")
    plan_id: str = Field(..., description="方案ID")
    month: int = Field(..., description="购买月数")
    total_amount: str = Field(..., description="实际支付金额")
    show_amount: str = Field(..., description="前端显示金额")
    status: int = Field(..., description="订单状态，2=已支付？")
    remark: str = Field("", description="备注")
    redeem_id: str = Field("", description="兑换码ID")
    product_type: int = Field(..., description="产品类型，0=普通商品？")
    discount: str = Field(..., description="折扣金额")
    sku_detail: List[SkuDetail] = Field(default_factory=list, description="SKU 明细列表")
    address_person: str = Field("", description="收货人姓名")
    address_phone: str = Field("", description="收货人电话")
    address_address: str = Field("", description="收货地址")


class WebhookData(BaseModel):
    type: str = Field(..., description="数据类型，如：order")
    order: Order = Field(..., description="订单数据")

class AFDianWebhook(BaseModel):
    ec: int = Field(..., description="状态码，如：200")
    em: str = Field(..., description="状态信息，如：ok")
    data: WebhookData = Field(..., description="具体数据")


class AFDianWebhookResponse(BaseModel):
    ec: int = Field(..., description="状态码，如：200")
    em: str = Field(..., description="状态信息，如：ok")

class AfDianNotify(_PluginBase):
    # 插件名称
    plugin_name = "爱发电Webhook通知"
    # 插件描述
    plugin_desc = "接收爱发电webhook订单消息并通知。"
    # 插件图标
    plugin_icon = "https://raw.githubusercontent.com/qcgzxw/MoviePilot-Plugins/main/icons/afdian.png"
    # 插件版本
    plugin_version = "1.0"
    # 插件作者
    plugin_author = "Owen"
    # 作者主页
    author_url = "https://github.com/qcgzxw/MoviePilot-Plugins"
    # 插件配置项ID前缀
    plugin_config_prefix = "afdiannotify_"
    # 加载顺序
    plugin_order = 30
    # 可使用的用户级别
    auth_level = 1

    # 任务执行间隔
    _enabled = False
    _notify = False
    _msgtype = None

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled")
            self._notify = config.get("notify")
            self._msgtype = config.get("msgtype")

    def handle_webhook(self, apikey: str, message: AFDianWebhook) -> AFDianWebhookResponse:
        """
        处理爱发电Webhook订单消息
        """
        result = AFDianWebhookResponse(ec=500, em="")
        if apikey != settings.API_TOKEN:
            result.em = "API密钥错误"
            return result
        try:
            order_info = message.data.order

            logger.info(
                f"收到爱发电订单通知: \n"
                f"  - out_trade_no={order_info.out_trade_no}\n"
                f"  - custom_order_id={order_info.custom_order_id}\n"
                f"  - user_id={order_info.user_id}\n"
                f"  - user_private_id={order_info.user_private_id}\n"
                f"  - total_amount={order_info.total_amount}\n"
                f"  - status={order_info.status}\n"
                f"  - sku_detail={order_info.sku_detail}"
            )

            if self._enabled and self._notify:
                mtype = NotificationType.Manual
                if self._msgtype:
                    mtype = NotificationType.__getitem__(str(self._msgtype)) or NotificationType.Manual
                text = (
                    f"爱发电订单通知\n"
                    f"订单号: {order_info.out_trade_no}\n"
                    f"自定义订单ID: {order_info.custom_order_id}\n"
                    f"用户ID: {order_info.user_id}\n"
                    f"金额: {order_info.total_amount}\n"
                    f"备注: {order_info.remark}\n"
                )
                self.post_message(
                    title="爱发电订单通知",
                    text=text,
                    mtype=mtype
                )
            result.ec = 200

        except Exception as e:
            logger.error(f"处理Webhook时出错: {str(e)}")
            result.em="服务器内部错误"

        return result


    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        """
        获取插件API
        [{
            "path": "/webhook",
            "endpoint": self.handle_webhook,
            "methods": ["POST"],
            "summary": "爱发电Webhook",
            "description": "接受爱发电Webhook订单消息并响应"
        }]
        """
        return [{
            "path": "/webhook",
            "endpoint": self.handle_webhook,
            "methods": ["POST"],
            "summary": "爱发电Webhook",
            "description": "接受爱发电Webhook订单消息并响应"
        }]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        # 编历 NotificationType 枚举，生成消息类型选项
        MsgTypeOptions = []
        for item in NotificationType:
            MsgTypeOptions.append({
                "title": item.value,
                "value": item.name
            })
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'notify',
                                            'label': '开启通知',
                                        }
                                    }
                                ]
                            },
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'multiple': False,
                                            'chips': True,
                                            'model': 'msgtype',
                                            'label': '消息类型',
                                            'items': MsgTypeOptions
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '爱发电Webhook配置URL：http://您的域名:端口/api/v1/plugin/AfDianNotify/webhook?apikey=*****。'
                                                    '此端点用于接收爱发电的订单Webhook。请确保网络可访问此URL。'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '如果安装插件后，收到Webhook时提示404，请重启MoviePilot以使插件生效。'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "notify": False,
            "msgtype": ""
        }

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self):
        """
        退出插件
        """
        pass
