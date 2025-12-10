import os
import sys
import json
import shutil
import gspread

# ================= 설정 =================
BASE_DIR = os.getcwd()
SHEET_NAME = '비디오관리_CMS'
OUTPUT_DIR = os.path.join(BASE_DIR, 'site')
TEMPLATE_EMBED = os.path.join(BASE_DIR, 'template_embed.html')
TEMPLATE_HUB = os.path.join(BASE_DIR, 'template_hub.html')
# ========================================

def get_sheet_data():
    print("🔄 구글 시트 연결 시도...")
    
    json_str = os.environ.get('GOOGLE_API_KEY')
    if not json_str:
        print("❌ [에러] GOOGLE_API_KEY가 없습니다.")
        sys.exit(1)

    try:
        # JSON 파싱
        creds_dict = json.loads(json_str)
        
        # [핵심] 줄바꿈 문자 강제 치환 (이건 필수입니다)
        if 'private_key' in creds_dict:
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')

        # gspread 최신 인증 방식 사용 (oauth2client 제거)
        gc = gspread.service_account_from_dict(creds_dict)
        
        sh = gc.open(SHEET_NAME)
        ws = sh.worksheet('Master_Mapping')
        records = ws.get_all_records()
        
        print(f"✅ 데이터 {len(records)}개 가져옴.")
        return records
        
    except Exception as e:
        print(f"❌ [구글 시트 에러] 연결 실패: {e}")
        # 어떤 에러인지 정확히 보기 위해 출력
        import traceback
        traceback.print_exc()
        sys.exit(1)

def build_site():
    # 1. 기존 폴더 정리
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(os.path.join(OUTPUT_DIR, 'embed'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, 'hub'), exist_ok=True)
    
    # 2. 템플릿 읽기
    if not os.path.exists(TEMPLATE_EMBED) or not os.path.exists(TEMPLATE_HUB):
        print("❌ 템플릿 파일이 없습니다.")
        sys.exit(1)

    with open(TEMPLATE_EMBED, 'r', encoding='utf-8') as f: tpl_embed = f.read()
    with open(TEMPLATE_HUB, 'r', encoding='utf-8') as f: tpl_hub = f.read()

    # 3. 데이터 처리
    data = get_sheet_data()
    
    grouped_data = {}
    valid_count = 0
    
    for row in data:
        # 카테고리가 '상세'인 행만 처리
        category = str(row.get('카테고리', '')).strip()
        if category != '상세':
            continue
        
        product_code = str(row.get('상품 코드', '')).strip()
        if not product_code or len(product_code) != 6:
            continue
        valid_count += 1
        
        video_id = str(row.get('Video ID', '')).strip()
        
        # Video ID가 없으면 embed 생성 스킵 (비유튜브 영상)
        if not video_id:
            print(f"⚠️ {product_code}: Video ID 없음 - embed 스킵")
            continue
        
        item = {
            'category': category,
            'video_id': video_id,
            'title': row.get('영상 제목', ''),
            'product_code': product_code
        }
        if product_code not in grouped_data:
            grouped_data[product_code] = []
        grouped_data[product_code].append(item)
        
    # 4. 파일 생성
    print("🔨 HTML 파일 생성 시작...")
    file_count = 0
    
    for code, videos in grouped_data.items():
        # Embed - '상세' 카테고리 영상만 (이미 필터링됨)
        target_vid = videos[0]['video_id'] if videos else None
        
        if target_vid:
            html = tpl_embed.replace('{{VIDEO_ID}}', target_vid)
            with open(os.path.join(OUTPUT_DIR, 'embed', f"{code}.html"), 'w', encoding='utf-8') as f:
                f.write(html)
        
        # Hub
        list_html = ""
        for v in videos:
            if not v['video_id']: continue
            list_html += f'<div class="card"><div class="video-box"><iframe src="https://www.youtube.com/embed/{v["video_id"]}" allowfullscreen></iframe></div><div class="desc"><span class="badge">{v["category"]}</span><h3>{v["title"]}</h3></div></div>'
        
        hub_html = tpl_hub.replace('{{PRODUCT_CODE}}', code).replace('{{VIDEO_LIST_HTML}}', list_html)
        with open(os.path.join(OUTPUT_DIR, 'hub', f"{code}.html"), 'w', encoding='utf-8') as f:
            f.write(hub_html)
        file_count += 1
        
    print(f"🎉 최종 완료! 생성된 페이지 수: {file_count}")
    if file_count == 0:
        print("❌ [경고] 생성된 파일이 0개입니다.")
        sys.exit(1)

if __name__ == '__main__':
    build_site()

