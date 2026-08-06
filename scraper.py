import json
import os
import re
from datetime import datetime
import pandas as pd
from playwright.sync_api import sync_playwright

ARTISTS = {
    "브로콜리너마저": "https://open.spotify.com/artist/1gq4XavqmZhqOzEkpFBz1j",
    "아도이": "https://open.spotify.com/artist/64sY7LsUjNE3ifONkftTXC",
    "우희준": "https://open.spotify.com/artist/0QPwpwjMdM0lU9NPmmqyEK",
    "이디오테잎": "https://open.spotify.com/artist/0OmQCkk1rR3DJ0Y2NRxp6Z",
    "키라라": "https://open.spotify.com/artist/6Q4tDWdAQdRjV4pAuqiHQW",
    "피치트럭하이재커스": "https://open.spotify.com/artist/4RBk8cCsxzo5v0rHu5EgPA",
    "김창완밴드": "https://open.spotify.com/artist/2bpghoDPX6onfPzQv570rM",
    "봉제인간": "https://open.spotify.com/artist/3zyq3DzSd4aue9Q7s1qMVu",
    "추다혜차지스": "https://open.spotify.com/artist/3ttQR1taRsySrYIc2U3iAA",
    "세이수미": "https://open.spotify.com/artist/4tvbo17gXpYgSr8sTlkaby"
}

def scrape():
    today = datetime.now().strftime("%Y-%m-%d")
    results = []

    print(f"=== [{today}] 스포티파이 데이터 수집 시작 ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/122.0.0.0 Safari/537.36"
        )

        for name, url in ARTISTS.items():
            print(f"수집 중: {name}")
            monthly_listeners = "정보 없음"
            followers = "정보 없음"
            try:
                page.goto(url, timeout=60000)
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(4000) # 동적 로딩 안정화 대기

                # 페이지 전체 텍스트 확보
                body_text = page.inner_text("body")

                # 1. 텍스트 패턴에서 숫자를 유연하게 탐색
                # 월별 청취자 패턴 탐색
                listeners_match = re.search(r'([0-9,]+)\s*(?:명의\s*)?월별 청취자|Monthly Listeners[:\s]*([0-9,]+)', body_text, re.IGNORECASE)
                if listeners_match:
                    monthly_listeners = listeners_match.group(1) or listeners_match.group(2)

                # 팔로워 패턴 탐색
                followers_match = re.search(r'([0-9,]+)\s*팔로워|Followers[:\s]*([0-9,]+)', body_text, re.IGNORECASE)
                if followers_match:
                    followers = followers_match.group(1) or followers_match.group(2)

                # 2. 텍스트로 못 찾은 경우 내부 데이터(__NEXT_DATA__) 구조 재탐색
                if monthly_listeners == "정보 없음" or followers == "정보 없음":
                    next_data = page.locator("script#__NEXT_DATA__")
                    if next_data.count() > 0:
                        j = json.loads(next_data.inner_text())
                        def search_json(node):
                            nonlocal monthly_listeners, followers
                            if isinstance(node, dict):
                                if "monthlyListeners" in node and monthly_listeners == "정보 없음":
                                    monthly_listeners = str(node["monthlyListeners"])
                                if "followers" in node and followers == "정보 없음":
                                    followers = str(node["followers"])
                                for k, v in node.items():
                                    search_json(v)
                            elif isinstance(node, list):
                                for item in node:
                                    search_json(item)
                        search_json(j)

                results.append({
                    "날짜": today,
                    "아티스트": name,
                    "월별 청취자": monthly_listeners,
                    "팔로워": followers,
                    "URL": url
                })
            except Exception as e:
                print(f"에러 발생 ({name}): {e}")
                results.append({
                    "날짜": today,
                    "아티스트": name,
                    "월별 청취자": "에러",
                    "팔로워": "에러",
                    "URL": url
                })

        browser.close()

    df_new = pd.DataFrame(results)
    csv_file = "spotify_history.csv"
    
    if os.path.exists(csv_file):
        df_old = pd.read_csv(csv_file)
        df_old = df_old[df_old["날짜"] != today] # 오늘 날짜 데이터 갱신을 위해 기존 것 제거 후 재추가
        df_final = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_final = df_new

    df_final.to_csv(csv_file, index=False, encoding="utf-8-sig")
    print("데이터 저장 완료!")

if __name__ == "__main__":
    scrape()
