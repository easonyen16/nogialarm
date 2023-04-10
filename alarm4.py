import os
import asyncio
import aiohttp
from aiohttp import ClientSession
from tqdm import tqdm
import UnityPy
from UnityPy.enums import TextureFormat
from UnityPy.export import Texture2DConverter
from PIL import Image

failed_downloads_file = "failed_downloads.txt"

def resize_image(image_path, new_size):
    with Image.open(image_path) as img:
        img_resized = img.resize(new_size, resample=Image.LANCZOS)
        img_resized.save(image_path)

def extract_image_from_unity_asset(asset_path):
    # 使用 UnityPy 加载资源
    #print("开始提取纹理")
    env = UnityPy.load(asset_path)

    # 遍历资源中的所有对象
    for obj in env.objects:
        # 输出对象的类型名称
        #print(f"Object type name: {obj.type.name}")

        # 如果对象是纹理类型（Texture2D）
        if obj.type.name == "Texture2D":
            # 解析纹理数据
            texture = obj.read()

            # 输出纹理对象的详细信息
            #print(f"Texture Name: {texture.name}")
            #print(f"Texture Format: {TextureFormat(texture.m_TextureFormat).name}")
            #print(f"Texture Dimensions: {texture.m_Width}x{texture.m_Height}")

            # 获取纹理对应的 PIL Image 对象
            image = texture.image

            # 为导出的图像创建新的文件名
            new_file_path = os.path.splitext(asset_path)[0] + "_extracted.png"
            # 保存图像数据到文件
            image.save(new_file_path)

            # 重新调整图片大小
            resize_image(new_file_path, (900, 1200))

            print(f"Extracted image saved to {new_file_path}")


def load_failed_downloads():
    if os.path.exists(failed_downloads_file):
        with open(failed_downloads_file, "r") as file:
            return set(file.read().splitlines())
    return set()

def save_failed_download(url):
    with open(failed_downloads_file, "a") as file:
        file.write(f"{url}\n")

async def download_file(url, save_path, session, failed_downloads, progress_bar):
    if os.path.exists(save_path) or url in failed_downloads:
        return False, False

    async with session.get(url) as response:
        if response.status == 200:
            content = await response.read()
            with open(save_path, "wb") as file:
                file.write(content)
            progress_bar.set_description(f"Downloading {save_path}")
            progress_bar.update(1)

            # 提取 Unity 资源中的图像
            try:
                extract_image_from_unity_asset(save_path)
            except Exception as e:
                print(f"Error extracting image from {save_path}: {e}")
                return False, True

            return True, False
        else:
            save_failed_download(url)
            progress_bar.update(1)
            return False, True



async def download_files_for_member(member_number, member_name, session, failed_downloads, progress_bar, star_ranks, card_numbers, star_levels):
    base_url = "https://res.nogizaka46-always.emtg.jp/asset/1.1.424/Android/card/card/card_"
    member_folder = f"member_{member_number}_{member_name}"
    os.makedirs(member_folder, exist_ok=True)

    tasks = []
    for star_rank in star_ranks:
        for card_number in card_numbers:
            for star_level in star_levels:
                file_name = f"{star_rank}{card_number}{member_number}{star_level}.png"
                url = base_url + file_name
                save_path = os.path.join(member_folder, file_name)
                tasks.append(download_file(url, save_path, session, failed_downloads, progress_bar))

    results, failures = zip(*await asyncio.gather(*tasks))
    new_downloads = sum(results)
    failed_downloads_count = sum(failures)
    return member_number, member_name, new_downloads, failed_downloads_count

async def main():
    members = {
        "01": "秋元",
        "12": "斋藤",
        "20": "铃木",
    }

    star_ranks = ["41"]
    card_numbers = [str(i).zfill(4) for i in range(0, 100)]
    star_levels = ["001", "002"]

    failed_downloads = load_failed_downloads()

    total_downloads = len(members) * len(star_ranks) * len(card_numbers) * len(star_levels)
    progress_bar = tqdm(total=total_downloads, ncols=100)

    async with ClientSession() as session:
        download_results = await asyncio.gather(*[download_files_for_member(member_number, member_name, session, failed_downloads, progress_bar, star_ranks, card_numbers, star_levels) for member_number, member_name in members.items()])

    progress_bar.close()

    for member_number, member_name, new_downloads, failed_downloads_count in download_results:
        print(f"Member {member_number} ({member_name}) downloaded {new_downloads} new cards, with {failed_downloads_count}failed attempts.")

if __name__ == "__main__":
    asyncio.run(main())
