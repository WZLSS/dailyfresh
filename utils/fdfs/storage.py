from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings


# 重写父类Storage的方法
class FDFSStorage(Storage):

    def __init__(self, client_conf=None, nginx_ip=None):
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if nginx_ip is None:
            nginx_ip = settings.FDFS_NGINX_IP
        self.nginx_ip = nginx_ip

    def _open(self, name, mode='rb'):
        # 打开文件时使用此方法
        pass

    def _save(self, name, content):
        # 保存文件时使用
        # name:上传文件的文件名
        # content:上传文件内容的File对象
        # 创建一个Fdfd_client对象
        client = Fdfs_client(self.client_conf)
        # 上传文件到fdst_dfs文件系统，按文件内容上传
        res = client.upload_by_buffer(content.read())
        print(res)
        # 返回值res为一个字典
        if res.get('Status') != 'Upload successed.':
            # 上传失败
            raise Exception('文件上传失败')
        # 获取返回的文件id
        filename = res.get('Remote file_id')
        return filename

    def exists(self, name):
        # django判断文件名是否可用
        return False

    def url(self, name):
        # 返回访问文件的url路径
        return self.nginx_ip + name
