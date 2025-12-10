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
        creds_dict = json.loads(json_str)
        if 'private_key' in creds_dict:
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')

        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open(SHEET_NAME)
        ws = sh.worksheet('Master_Mapping')
        records = ws.get_all_records()
        
        print(f"✅ 데이터 {len(records)}개 가져옴.")
        return records
        
    except Exception as e:
        print(f"❌ [구글 시트 에러] 연결 실패: {e}")
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
    
    # ★★★ 디버깅: 첫 번째 행의 컬럼명 출력 ★★★
    if data:
        print("\n📋 [디버그] 시트 컬럼명:")
        print(list(data[0].keys()))
        print("\n📋 [디버그] 첫 번째 행 데이터:")
        for key, value in data[0].items():
            print(f"  '{key}': '{value}'")
        print()
    
    grouped_data = {}
    valid_count = 0
    
    for idx, row in enumerate(data):
        # ★★★ 디버깅: 각 행 처리 과정 출력 ★★★
        category = str(row.get('카테고리', '')).strip()
        product_code = str(row.get('상품 코드', '')).strip()
        video_id = str(row.get('Video ID', '')).strip()
        
        print(f"행 {idx+2}: 카테고리='{category}', 상품코드='{product_code}', VideoID='{video_id}'")
        
        # 카테고리가 '상세'인 행만 처리
        if category != '상세':
            print(f"  → 스킵 (카테고리가 '상세'가 아님)")
            continue
        
        # 상품 코드 검증
        if not product_code:
            print(f"  → 스킵 (상품 코드 없음)")
            continue
            
        # Video ID 검증
        if not video_id:
            print(f"  → 스킵 (Video ID 없음)")
            continue
        
        valid_count += 1
        print(f"  → ✅ 유효")
        
        item = {
            'category': category,
            'video_id': video_id,
            'title': row.get('영상 제목', ''),
            'product_code': product_code
        }
        
        if product_code not in grouped_data:
            grouped_data[product_code] = []
        grouped_data[product_code].append(item)
    
    print(f"\n📊 유효한 행: {valid_count}개")
    print(f"📊 그룹 수: {len(grouped_data)}개")
        
    # 4. 파일 생성
    print("\n🔨 HTML 파일 생성 시작...")
    file_count = 0
    
    for code, videos in grouped_data.items():
        # Embed
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
        print("\n💡 확인사항:")
        print("  1. '카테고리' 컬럼에 '상세' 값이 있는지")
        print("  2. '상품 코드' 컬럼에 값이 있는지")
        print("  3. 'Video ID' 컬럼에 값이 있는지")
        sys.exit(1)

if __name__ == '__main__':
    build_site()
