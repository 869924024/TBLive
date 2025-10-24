from . import SunnyDLL
from ctypes import *
class CertManager:
    SSL_CLIENT_AUTH_NO_CLIENT_CERT = 0
    """ 不请求客户端证书，任何发送的证书不会被验证。 """
    SSL_CLIENT_AUTH_REQUEST_CLIENT_CERT = 1
    """ 请求客户端证书，但不强制客户端发送。 """
    SSL_CLIENT_AUTH_REQUIRE_ANY_CLIENT_CERT = 2
    """ 请求客户端证书，必须至少发送一个证书，但不要求证书有效。 """
    SSL_CLIENT_AUTH_VERIFY_CLIENT_CERT_IF_GIVEN = 3
    """ 请求客户端证书，如果提供则需验证其有效性。 """
    SSL_CLIENT_AUTH_REQUIRE_AND_VERIFY_CLIENT_CERT = 4
    """ 请求客户端证书，必须发送并验证有效证书。 """

    def __init__(self):
        self.certificate_context = SunnyDLL.DLLSunny.CreateCertificate()
        self.skip_verify(True)

    def __del__(self):
        SunnyDLL.DLLSunny.RemoveCertificate(self.certificate_context)

    def skip_verify(self, skip: bool) -> None:
        """ 设置是否跳过主机验证，默认为 True。

        参数:
        - skip: 如果为 True，跳过主机验证；否则进行主机验证。
        """
        if not isinstance(skip, bool):
            raise TypeError("参数类型错误：skip 应为布尔值")
        SunnyDLL.DLLSunny.SetInsecureSkipVerify(self.certificate_context, skip)

    def reset(self) -> None:
        """ 重新创建证书上下文。 """
        if self.certificate_context > 0:
            SunnyDLL.DLLSunny.RemoveCertificate(self.certificate_context)
        self.certificate_context = SunnyDLL.DLLSunny.CreateCertificate()
        self.skip_verify(True)

    def load_p12(self, p12_file_path: str, p12_file_password: str) -> None:
        """ 从 P12 文件载入证书。

        参数:
        - p12_file_path: P12 文件的路径。
        - p12_file_password: P12 文件的密码。
        """
        if not isinstance(p12_file_path, str):
            raise TypeError("参数类型错误：p12_file_path 应为字符串")
        if not isinstance(p12_file_password, str):
            raise TypeError("参数类型错误：p12_file_password 应为字符串")

        SunnyDLL.DLLSunny.LoadP12Certificate(
            self.certificate_context,
            create_string_buffer(p12_file_path.encode("utf-8")),
            create_string_buffer(p12_file_password.encode("utf-8"))
        )

    def load_p12_x509_key_pair(self, cert_file_path: str, key_file_path: str) -> None:
        """ 从 PEM 编码的证书和私钥文件载入公钥/私钥对。

        参数:
        - cert_file_path: 证书文件的路径。
        - key_file_path: 私钥文件的路径。
        """
        if not isinstance(cert_file_path, str):
            raise TypeError("参数类型错误：cert_file_path 应为字符串")
        if not isinstance(key_file_path, str):
            raise TypeError("参数类型错误：key_file_path 应为字符串")

        SunnyDLL.DLLSunny.LoadX509KeyPair(
            self.certificate_context,
            create_string_buffer(cert_file_path.encode("utf-8")),
            create_string_buffer(key_file_path.encode("utf-8"))
        )

    def load_x509_cert(self, host: str, cert_value: str, key_value: str) -> None:
        """ 从给定的证书和私钥值载入 X.509 证书，默认跳过主机验证。

        参数:
        - host: 证书适用的主机名。
        - cert_value: 证书的 PEM 编码字符串。
        - key_value: 私钥的 PEM 编码字符串。
        """
        if not isinstance(host, str):
            raise TypeError("参数类型错误：host 应为字符串")
        if not isinstance(cert_value, str):
            raise TypeError("参数类型错误：cert_value 应为字符串")
        if not isinstance(key_value, str):
            raise TypeError("参数类型错误：key_value 应为字符串")

        SunnyDLL.DLLSunny.LoadX509Certificate(
            self.certificate_context,
            create_string_buffer(host.encode("utf-8")),
            create_string_buffer(cert_value.encode("utf-8")),
            create_string_buffer(key_value.encode("utf-8"))
        )

    def set_server_name(self, name: str) -> None:
        """ 设置证书上的主机名，需先载入或创建证书。

        参数:
        - name: 证书的主机名。
        """
        if not isinstance(name, str):
            raise TypeError("参数类型错误：name 应为字符串")
        SunnyDLL.DLLSunny.SetServerName(self.certificate_context, create_string_buffer(name.encode("utf-8")))

    def get_server_name(self) -> str:
        """ 返回证书上的主机名，需先载入证书。 """
        return SunnyDLL.PointerToText(SunnyDLL.DLLSunny.GetServerName(self.certificate_context))

    def context(self) -> int:
        """ 返回当前证书上下文。 """
        return self.certificate_context

    def add_cert_pool_path(self, file_path: str) -> None:
        """ 添加客户端信任的证书文件。

        参数:
        - file_path: 信任证书文件的路径。
        """
        if not isinstance(file_path, str):
            raise TypeError("参数类型错误：file_path 应为字符串")
        SunnyDLL.DLLSunny.AddCertPoolPath(self.certificate_context, create_string_buffer(file_path.encode("utf-8")))

    def add_cert_pool_text(self, value: str) -> None:
        """ 添加客户端信任的证书文本。

        参数:
        - value: PEM 编码的证书文本。
        """
        if not isinstance(value, str):
            raise TypeError("参数类型错误：value 应为字符串")
        SunnyDLL.DLLSunny.AddCertPoolText(self.certificate_context, create_string_buffer(value.encode("utf-8")))

    def add_client_auth(self, mode: int = SSL_CLIENT_AUTH_NO_CLIENT_CERT) -> None:
        """ 设置客户端认证模式，0-4 对应 SSL_CLIENT_AUTH_ 常量。

        参数:
        - mode: 客户端认证模式，默认为 SSL_CLIENT_AUTH_NO_CLIENT_CERT。
        """
        if not isinstance(mode, int):
            raise TypeError("参数类型错误：mode 应为整数")
        SunnyDLL.DLLSunny.AddClientAuth(self.certificate_context, mode)

    def create(self, common_name: str, country: str = "CN", organization: str = "Sunny",
                  organizational_unit: str = "Sunny", province: str = "BeiJing", locality: str = "BeiJing",
                  not_after: int = 3650) -> bool:
        """
        创建 CA 证书。

        参数:
        - common_name: 证书的通用名称（Common Name）。
        - country: 证书所属国家，默认为 "CN"。
        - organization: 证书存放的公司名称，默认为 "Sunny"。
        - organizational_unit: 证书所属部门名称，默认为 "Sunny"。
        - province: 证书签发机构所在省，默认为 "BeiJing"。
        - locality: 证书签发机构所在市，默认为 "BeiJing"。
        - not_after: 证书有效期（天），默认为 3650 天。
        """
        if not isinstance(common_name, str):
            raise TypeError("参数类型错误：common_name 应为字符串")
        if not isinstance(country, str):
            raise TypeError("参数类型错误：country 应为字符串")
        if not isinstance(organization, str):
            raise TypeError("参数类型错误：organization 应为字符串")
        if not isinstance(organizational_unit, str):
            raise TypeError("参数类型错误：organizational_unit 应为字符串")
        if not isinstance(province, str):
            raise TypeError("参数类型错误：province 应为字符串")
        if not isinstance(locality, str):
            raise TypeError("参数类型错误：locality 应为字符串")
        if not isinstance(not_after, int):
            raise TypeError("参数类型错误：not_after 应为整数")

        result = SunnyDLL.DLLSunny.CreateCA(
            self.certificate_context,
            create_string_buffer(country.encode("utf-8")),
            create_string_buffer(organization.encode("utf-8")),
            create_string_buffer(organizational_unit.encode("utf-8")),
            create_string_buffer(province.encode("utf-8")),
            create_string_buffer(common_name.encode("utf-8")),
            create_string_buffer(locality.encode("utf-8")),
            2048,
            not_after
        )
        return bool(result)

    def _replace_line_endings(self, text: str) -> str:
        """ 替换文本中的行结束符为 CRLF。 """
        if not isinstance(text, str):
            raise TypeError("参数类型错误：text 应为字符串")
        return text.replace("\r", "").replace("\n", "\r\n")

    def export_pub_key(self) -> str:
        """ 导出公钥。 """
        return self._replace_line_endings(SunnyDLL.PointerToText(SunnyDLL.DLLSunny.ExportPub(self.certificate_context)))

    def export_private_key(self) -> str:
        """ 导出私钥。 """
        return self._replace_line_endings(SunnyDLL.PointerToText(SunnyDLL.DLLSunny.ExportKEY(self.certificate_context)))

    def export_ca_cert(self) -> str:
        """ 导出 CA 证书。 """
        return self._replace_line_endings(SunnyDLL.PointerToText(SunnyDLL.DLLSunny.ExportCA(self.certificate_context)))

    def get_common_name(self) -> str:
        """ 获取证书的通用名称 (Common Name)。 """
        return self._replace_line_endings(SunnyDLL.PointerToText(SunnyDLL.DLLSunny.GetCommonName(self.certificate_context)))

    def export_p12(self, save_file_path: str, password: str) -> bool:
        """ 导出 P12 文件。

        参数:
        - save_file_path: 导出 P12 文件的保存路径。
        - password: P12 文件的密码。
        """
        if not isinstance(save_file_path, str):
            raise TypeError("参数类型错误：save_file_path 应为字符串")
        if not isinstance(password, str):
            raise TypeError("参数类型错误：password 应为字符串")

        result = SunnyDLL.DLLSunny.ExportP12(
            self.certificate_context,
            create_string_buffer(save_file_path.encode("utf-8")),
            create_string_buffer(password.encode("utf-8"))
        )
        return bool(result)