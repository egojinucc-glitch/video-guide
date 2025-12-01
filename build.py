import os
import shutil
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ================= 설정 =================
# 현재 실행 중인 파일(build.py)의 폴더 경로를 구함
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 파일 경로들 절대경로로 재설정
JSON_FILE = os.path.join(BASE_DIR, 'videocms-479902-4d5c90b373aa.json') # 본인 키 파일명 확인
SHEET_NAME = '비디오관리_CMS'
OUTPUT_DIR = os.path.join(BASE_DIR, 'site')  # 결과물 폴더도 절대경로로
TEMPLATE_EMBED = os.path.join(BASE_DIR, 'template_embed.html')
TEMPLATE_HUB = os.path.join(BASE_DIR, 'template_hub.html')
# ========================================

def get_sheet_data():
    """구글 시트에서 데이터 가져오기"""
    print("🔄 구글 시트 연결 중...")
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
    client = gspread.authorize(creds)
    
    sh = client.open(SHEET_NAME)
    ws = sh.worksheet('Master_Mapping')
    records = ws.get_all_records()
    print(f"✅ 데이터 {len(records)}개 가져옴.")
    return records

def build_site():
    # 1. 기존 결과물 폴더 비우고 새로 만들기
    if os.path.exists(OUTPUT_DIR):
        try:
            shutil.rmtree(OUTPUT_DIR)
        except OSError as e:
            print(f"⚠️ 기존 폴더 삭제 실패 (무시하고 진행): {e}")

    # 폴더 생성
    os.makedirs(os.path.join(OUTPUT_DIR, 'embed'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, 'hub'), exist_ok=True)
    
    # 2. 템플릿 읽기 (절대경로 사용)
    try:
        with open(TEMPLATE_EMBED, 'r', encoding='utf-8') as f:
            tpl_embed = f.read()
        with open(TEMPLATE_HUB, 'r', encoding='utf-8') as f:
            tpl_hub = f.read()
    except FileNotFoundError as e:
        print(f"❌ 템플릿 파일을 찾을 수 없습니다: {e}")
        print(f"👉 파일이 {BASE_DIR} 폴더 안에 있는지 확인하세요.")
        return
        
    # 3. 데이터 정리 (SKU별로 묶기)
    try:
        data = get_sheet_data()
    except Exception as e:
        print(f"❌ 구글 시트 연결 실패: {e}")
        return

    grouped_data = {}
    
    for row in data:
        raw_code = str(row.get('이지어드민코드', '')).strip()
        if not raw_code: continue
        
        ez_code = raw_code.lstrip('0') 
        
        item = {
            'category': row.get('카테고리', ''),
            'video_id': row.get('Video ID', ''),
            'title': row.get('영상제목(자동)', '')
        }
        
        if ez_code not in grouped_data:
            grouped_data[ez_code] = []
        grouped_data[ez_code].append(item)
        
    # 4. 파일 생성
    print("🔨 HTML 파일 생성 시작...")
    count = 0
    
    for code, videos in grouped_data.items():
        # [A] 상세페이지용 (embed)
        target_vid = next((v['video_id'] for v in videos if v['category'] == '상세영상'), None)
        if not target_vid and videos: target_vid = videos[0]['video_id']
        
        if target_vid:
            html = tpl_embed.replace('{{VIDEO_ID}}', target_vid)
            # 저장 경로도 절대경로로
            save_path = os.path.join(OUTPUT_DIR, 'embed', f"{code}.html")
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(html)
        
        # [B] QR페이지용 (hub)
        list_html = ""
        for v in videos:
            if not v['video_id']: continue
            list_html += f"""
            <div class="card">
                <div class="video-box">
                    <iframe src="https://www.youtube.com/embed/{v['video_id']}" allowfullscreen></iframe>
                </div>
                <div class="desc">
                    <span class="badge">{v['category']}</span>
                    <h3>{v['title']}</h3>
                </div>
            </div>
            """
        
        hub_html = tpl_hub.replace('{{EZ_CODE}}', code).replace('{{VIDEO_LIST_HTML}}', list_html)
        save_path = os.path.join(OUTPUT_DIR, 'hub', f"{code}.html")
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(hub_html)
            
        count += 1
        
    # 인덱스 페이지
    with open(os.path.join(OUTPUT_DIR, "index.html"), 'w', encoding='utf-8') as f:
        f.write("<h1>Video CMS System</h1><p>Github Pages deploy success.</p>")

    print(f"🎉 완료! 총 {count}개의 상품 페이지가 '{OUTPUT_DIR}' 폴더에 생성되었습니다.")

if __name__ == '__main__':
    build_site()