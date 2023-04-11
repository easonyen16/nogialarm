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
    env = UnityPy.load(asset_path)
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            texture = obj.read()
            image = texture.image
            new_file_path = os.path.splitext(asset_path)[0] + "_extracted.png"
            image.save(new_file_path)
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

async def download_file(url, save_path, session, failed_downloads, progress_bar, prefix):
    if os.path.exists(save_path) or url in failed_downloads:
        return False, False

    async with session.get(url) as response:
        if response.status == 200:
            content = await response.read()
            with open(save_path, "wb") as file:
                file.write(content)

            new_save_path = os.path.join(os.path.dirname(save_path), prefix + os.path.basename(save_path))
            os.rename(save_path, new_save_path)

            progress_bar.set_description(f"Downloading {new_save_path}")
            progress_bar.update(1)
            try:
                extract_image_from_unity_asset(new_save_path)
            except Exception as e:
                print(f"Error extracting image from {new_save_path}: {e}")
                return False, True

            return True, False
        else:
            save_failed_download(url)
            progress_bar.update(1)
            return False, True

async def download_files_for_member(member_number, member_name, session, failed_downloads, progress_bar, star_ranks, card_numbers, star_levels):
    base_url_card = "https://res.nogizaka46-always.emtg.jp/asset/1.1.424/Android/card/card/card_"
    base_url_photo = "https://res.nogizaka46-always.emtg.jp/asset/1.1.424/Android/card/photo/photo_"
    member_folder = f"member_{member_number}_{member_name}"
    os.makedirs(member_folder, exist_ok=True)

    tasks = []
    for star_rank in star_ranks:
        for card_number in card_numbers:
            for star_level in star_levels:
                file_name = f"{star_rank}{card_number}{member_number}{star_level}.png"
                url_card = base_url_card + file_name
                save_path_card = os.path.join(member_folder, file_name)
                tasks.append(download_file(url_card, save_path_card, session, failed_downloads, progress_bar, "card_"))

                url_photo = base_url_photo + file_name
                save_path_photo = os.path.join(member_folder, file_name)
                tasks.append(download_file(url_photo, save_path_photo, session, failed_downloads, progress_bar, "photo_"))

    results, failures = zip(*await asyncio.gather(*tasks))
    new_downloads = sum(results)
    failed_downloads_count = sum(failures)
    return member_number, member_name, new_downloads, failed_downloads_count

async def main():
    members = {
        "01": "秋元真夏",
        "12": "齋藤飛鳥",
        "20": "鈴木絢音",
        "27": "樋口日奈",
        "34": "和田まあや",
        "35": "伊藤理々杏",
        "36": "岩本蓮加",
        "37": "梅澤美波",
        "39": "久保史緒里",
        "40": "阪口珠美",
        "41": "佐藤楓",
        "42": "中村麗乃",
        "43": "向井葉月",
        "44": "山下美月",
        "45": "吉田綾乃クリスティー",
        "46": "与田祐希",
        "48": "遠藤さくら",
        "49": "賀喜遥香",
        "50": "掛橋沙耶香",
        "51": "金川紗耶",
        "52": "北川悠理",
        "53": "柴田柚菜",
        "54": "清宮レイ",
        "55": "田村真佑",
        "56": "筒井あやめ",
        "57": "早川聖来",
        "58": "矢久保美緒",
        "59": "黒見明香",
        "60": "佐藤璃果",
        "61": "林瑠奈",
        "62": "松尾美佑",
        "63": "弓木奈於",
        "64": "五百城茉央",
        "65": "池田瑛紗",
        "66": "一ノ瀬美空",
        "67": "井上和",
        "68": "岡本姫奈",
        "69": "小川彩",
        "70": "奥田いろは",
        "71": "川﨑桜",
        "72": "菅原咲月",
        "73": "冨里奈央",
        "74": "中西アルノ",
    }

    star_ranks = ["11","21","31","41"]
    card_numbers = [str(i).zfill(4) for i in range(0, 1700)]
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
