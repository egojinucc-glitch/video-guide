import os
import shutil
import sys  # 에러 발생 시 강제 종료를 위해 추가
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ================= 설정 =================
# 현재 작업 경로 확인
BASE_DIR = os.getcwd()
print(f"📍 현재 작업 위치: {BASE_DIR}")
print(f"📂 폴더 내 파일 목록: {os.listdir(BASE_DIR)}")

# 파일명 확인 (대소문자 정확해야 함)
JSON_FILENAME = 'videocms-479902-4d5c90b373aa.json' # 님 파일명
JSON_FILE = os.path.join(BASE_DIR, JSON_FILENAME)

SHEET_NAME = '비디오관리_CMS'
OUTPUT_DIR = os.path.join(BASE_DIR, 'site')
TEMPLATE_EMBED = os.path.join(BASE_DIR, 'template_embed.html')
TEMPLATE_HUB = os.path.join(BASE_DIR, 'template_hub.html')
# ========================================

def get_sheet_data():
    print("🔄 구글 시트 연결 시도...")
    
    # 1. 키 파일 존재 여부 확인
    if not os.path.exists(JSON_FILE):
        print(f"❌ [치명적 에러] 키 파일이 없습니다: {JSON_FILE}")
        print("👉 깃허브에 JSON 파일을 업로드했는지 확인하세요.")
        sys.exit(1) # 강제 종료 (빨간불 뜨게 함)

    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
        client = gspread.authorize(creds)
        
        sh = client.open(SHEET_NAME)
        ws = sh.worksheet('Master_Mapping')
        records = ws.get_all_records()
        
        if len(records) == 0:
            print("⚠️ [경고] 시트에는 연결됐는데 데이터가 0개입니다.")
            print("👉 Master_Mapping 시트 1행(헤더)이 정확한지 확인하세요.")
        else:
            print(f"✅ 데이터 {len(records)}개 가져옴.")
            
        return records
        
    except Exception as e:
        print(f"❌ [구글 시트 에러] 연결 실패: {e}")
        sys.exit(1)

def build_site():
    # 1. 기존 폴더 정리
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(os.path.join(OUTPUT_DIR, 'embed'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, 'hub'), exist_ok=True)
    
    # 2. 템플릿 읽기
    if not os.path.exists(TEMPLATE_EMBED) or not os.path.exists(TEMPLATE_HUB):
        print("❌ [치명적 에러] HTML 템플릿 파일이 없습니다.")
        sys.exit(1)

    with open(TEMPLATE_EMBED, 'r', encoding='utf-8') as f: tpl_embed = f.read()
    with open(TEMPLATE_HUB, 'r', encoding='utf-8') as f: tpl_hub = f.read()

    # 3. 데이터 처리
    data = get_sheet_data()
    
    grouped_data = {}
    valid_count = 0
    
    for row in data:
        raw_code = str(row.get('이지어드민코드', '')).strip()
        if not raw_code: continue
        
        ez_code = raw_code.lstrip('0')
        valid_count += 1
        
        item = {
            'category': row.get('카테고리', ''),
            'video_id': row.get('Video ID', ''),
            'title': row.get('영상제목(자동)', '')
        }
        
        if ez_code not in grouped_data:
            grouped_data[ez_code] = []
        grouped_data[ez_code].append(item)
        
    print(f"📊 유효한 상품 코드: {len(grouped_data)}개 (총 데이터 행: {valid_count})")

    # 4. 파일 생성
    print("🔨 HTML 파일 생성 시작...")
    file_count = 0
    
    for code, videos in grouped_data.items():
        # Embed
        target_vid = next((v['video_id'] for v in videos if v['category'] == '상세영상'), None)
        if not target_vid and videos: target_vid = videos[0]['video_id']
        
        if target_vid:
            html = tpl_embed.replace('{{VIDEO_ID}}', target_vid)
            with open(os.path.join(OUTPUT_DIR, 'embed', f"{code}.html"), 'w', encoding='utf-8') as f:
                f.write(html)
        
        # Hub
        list_html = ""
        for v in videos:
            if not v['video_id']: continue
            list_html += f'<div class="card"><div class="video-box"><iframe src="https://www.youtube.com/embed/{v["video_id"]}" allowfullscreen></iframe></div><div class="desc"><span class="badge">{v["category"]}</span><h3>{v["title"]}</h3></div></div>'
        
        hub_html = tpl_hub.replace('{{EZ_CODE}}', code).replace('{{VIDEO_LIST_HTML}}', list_html)
        with open(os.path.join(OUTPUT_DIR, 'hub', f"{code}.html"), 'w', encoding='utf-8') as f:
            f.write(hub_html)
            
        file_count += 1
        
    # 인덱스 생성
    with open(os.path.join(OUTPUT_DIR, "index.html"), 'w', encoding='utf-8') as f:
        f.write("<h1>Video CMS</h1>")

    print(f"🎉 최종 완료! 생성된 페이지 수: {file_count}")
    
    # 💥 중요: 파일이 하나도 안 만들어졌으면 에러 처리!
    if file_count == 0:
        print("❌ [경고] 생성된 파일이 0개입니다. 그래서 배포할 게 없습니다.")
        sys.exit(1) # 강제로 빨간불 띄움

if __name__ == '__main__':
    build_site()
