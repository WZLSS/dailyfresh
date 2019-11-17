from fdfs_client.client import Fdfs_client
from django.conf import settings
import django
import os


def upload():
    # print(settings.STATICFILES_DIRS + "/images")

    # 文件操作的知识，目录下面的所有文件
    images_path = settings.STATICFILES_DIRS[0] + "/images/"
    images_goods_path = settings.STATICFILES_DIRS[0] + "/images/goods/"
    # files = os.listdir(settings.STATICFILES_DIRS[0] + "/images")
    # print(l)

    # 连接到fdfs的客户端，准备上传文件到Storage server
    client = Fdfs_client(settings.FDFS_CLIENT_CONF)

    # 遍历出两个图片路径
    with open('./log.txt', 'w') as log_file:  # 这一步是记录上传信息的
        for path in [images_path, images_goods_path]:
            # 遍历出该路径下面的所有图片
            for file in os.listdir(path):
                # 将上传到fdfs文件存储系统
                try:
                    # 通过文件名字上传
                    # ret = client.upload_by_filename(path + file)
                    # 通过字节上传文件
                    with open(path + file, 'rb') as tem_file:
                        ret = client.upload_by_buffer(tem_file.read())
                except:
                    # print(1111)
                    # print(path + file)
                    # 这里经过测试，必须包裹起来，否则出现上传到一半就错误
                    ret = None
                # return dict
                # {
                #     'Group name': group_name,
                #     'Remote file_id': remote_file_id,
                #     'Status': 'Upload successed.',
                #     'Local file name': local_file_name,
                #     'Uploaded size': upload_size,
                #     'Storage IP': storage_ip
                # }
                if ret is None:
                    print("上传文件 %s 失败了" % (path + file))
                    # raise Exception("连接fdfs tracker 出错")
                else:
                    if ret['Status'] != 'Upload successed.':
                        print("%s-->传到fdfs出错" % (path + file))
                    log_file.writelines(ret['Local file name'] + "-->" + ret['Remote file_id'] + "\n")


def file_length():
    images_path = settings.STATICFILES_DIRS[0] + "/images/"
    images_goods_path = settings.STATICFILES_DIRS[0] + "/images/goods/"
    print(len(os.listdir(images_path)) + len(os.listdir(images_goods_path)))


if __name__ == '__main__':
    # 初始化django应用程序，否则无法使用settings里面的东西
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
    django.setup()
    # file_length()
    upload()
