import os
import sys
import json
import shutil
import gspread
import re

# ================= 설정 =================
BASE_DIR = os.getcwd()
SHEET_NAME = '비디오관리_CMS'
OUTPUT_DIR = os.path.join(BASE_DIR, 'site')
TEMPLATE_EMBED = os.path.join(BASE_DIR, 'template_embed.html')
TEMPLATE_HUB = os.path.join(BASE_DIR, 'template_hub.html')

# 디버그 모드 (환경변수로 제어)
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
# ========================================

def log(msg, level='info'):
    """로그 출력 (DEBUG 모드일 때만 상세 출력)"""
    if level == 'debug' and not DEBUG:
        return
    print(msg)

def get_sheet_data():
    log("🔄 구글 시트 연결 시도...")
    
    json_str = os.environ.get('GOOGLE_API_KEY')
    if not json_str:
        log("❌ [에러] GOOGLE_API_KEY가 없습니다.")
        sys.exit(1)

    try:
        creds_dict = json.loads(json_str)
        if 'private_key' in creds_dict:
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')

        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open(SHEET_NAME)
        ws = sh.worksheet('Master_Mapping')
        records = ws.get_all_records()
        
        log(f"✅ 데이터 {len(records)}개 가져옴.")
        return records
        
    except Exception as e:
        log(f"❌ [구글 시트 에러] 연결 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def validate_product_code(code):
    """상품 코드 유효성 검사 (6자리 숫자)"""
    if not code:
        return False, "비어있음"
    
    code_str = str(code).strip()
    
    # 숫자로 변환됐을 수 있으므로 zfill로 6자리 맞춤
    if code_str.isdigit():
        code_str = code_str.zfill(6)
    
    if not re.match(r'^\d{6}$', code_str):
        return False, f"6자리 숫자 아님 ('{code_str}')"
    
    return True, code_str

def validate_video_id(video_id):
    """유튜브 Video ID 유효성 검사"""
    if not video_id:
        return False, "비어있음"
    
    vid = str(video_id).strip()
    
    # 유튜브 Video ID는 보통 11자리
    if not re.match(r'^[a-zA-Z0-9_-]{10,12}$', vid):
        return False, f"유효하지 않은 형식 ('{vid}')"
    
    return True, vid

def build_site():
    # 1. 기존 폴더 정리
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(os.path.join(OUTPUT_DIR, 'embed'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, 'hub'), exist_ok=True)
    
    # 2. 템플릿 읽기
    if not os.path.exists(TEMPLATE_EMBED):
        log(f"❌ 템플릿 파일이 없습니다: {TEMPLATE_EMBED}")
        sys.exit(1)
    if not os.path.exists(TEMPLATE_HUB):
        log(f"❌ 템플릿 파일이 없습니다: {TEMPLATE_HUB}")
        sys.exit(1)

    with open(TEMPLATE_EMBED, 'r', encoding='utf-8') as f:
        tpl_embed = f.read()
    with open(TEMPLATE_HUB, 'r', encoding='utf-8') as f:
        tpl_hub = f.read()

    # 3. 데이터 처리
    data = get_sheet_data()
    
    if not data:
        log("❌ 시트에 데이터가 없습니다.")
        sys.exit(1)
    
    # 컬럼명 확인 (디버그)
    log(f"\n📋 [디버그] 시트 컬럼명: {list(data[0].keys())}", 'debug')
    
    grouped_data = {}
    stats = {
        'total': len(data),
        'skipped_category': 0,
        'skipped_product_code': 0,
        'skipped_video_id': 0,
        'valid': 0
    }
    
    for idx, row in enumerate(data):
        row_num = idx + 2  # 시트 기준 행번호
        
        # 카테고리 확인
        category = str(row.get('카테고리', '')).strip()
        if category != '상세':
            log(f"행 {row_num}: 스킵 (카테고리='{category}')", 'debug')
            stats['skipped_category'] += 1
            continue
        
        # 상품 코드 검증
        raw_code = row.get('상품 코드', '')
        is_valid, product_code = validate_product_code(raw_code)
        if not is_valid:
            log(f"행 {row_num}: 스킵 (상품코드 {product_code})", 'debug')
            stats['skipped_product_code'] += 1
            continue
        
        # Video ID 검증
        raw_vid = row.get('Video ID', '')
        is_valid, video_id = validate_video_id(raw_vid)
        if not is_valid:
            log(f"행 {row_num}: 스킵 (VideoID {video_id})", 'debug')
            stats['skipped_video_id'] += 1
            continue
        
        stats['valid'] += 1
        log(f"행 {row_num}: ✅ 유효 (코드={product_code}, VID={video_id})", 'debug')
        
        item = {
            'category': category,
            'video_id': video_id,
            'title': str(row.get('영상 제목', '')).strip(),
            'product_code': product_code
        }
        
        if product_code not in grouped_data:
            grouped_data[product_code] = []
        grouped_data[product_code].append(item)
    
    # 통계 출력
    log(f"\n📊 처리 결과:")
    log(f"  - 전체 행: {stats['total']}개")
    log(f"  - 카테고리 필터: {stats['skipped_category']}개 스킵")
    log(f"  - 상품코드 오류: {stats['skipped_product_code']}개 스킵")
    log(f"  - VideoID 오류: {stats['skipped_video_id']}개 스킵")
    log(f"  - 유효 데이터: {stats['valid']}개")
    log(f"  - 그룹 수: {len(grouped_data)}개")
        
    # 4. 파일 생성
    log("\n🔨 HTML 파일 생성 시작...")
    file_count = 0
    
    for code, videos in grouped_data.items():
        # Embed 파일
        target_vid = videos[0]['video_id'] if videos else None
        
        if target_vid:
            html = tpl_embed.replace('{{VIDEO_ID}}', target_vid)
            embed_path = os.path.join(OUTPUT_DIR, 'embed', f"{code}.html")
            with open(embed_path, 'w', encoding='utf-8') as f:
                f.write(html)
            log(f"  📄 embed/{code}.html 생성", 'debug')
        
        # Hub 파일
        list_html = ""
        for v in videos:
            if not v['video_id']:
                continue
            title = v['title'] if v['title'] else '제목 없음'
            list_html += f'''<div class="card">
    <div class="video-box">
        <iframe src="https://www.youtube.com/embed/{v["video_id"]}" allowfullscreen></iframe>
    </div>
    <div class="desc">
        <span class="badge">{v["category"]}</span>
        <h3>{title}</h3>
    </div>
</div>
'''
        
        hub_html = tpl_hub.replace('{{PRODUCT_CODE}}', code).replace('{{VIDEO_LIST_HTML}}', list_html)
        hub_path = os.path.join(OUTPUT_DIR, 'hub', f"{code}.html")
        with open(hub_path, 'w', encoding='utf-8') as f:
            f.write(hub_html)
        log(f"  📄 hub/{code}.html 생성", 'debug')
        
        file_count += 1
    
    # 최종 결과
    log(f"\n🎉 완료! 생성된 페이지: {file_count}개")
    
    if file_count == 0:
        log("\n❌ [경고] 생성된 파일이 0개입니다.")
        log("\n💡 확인사항:")
        log("  1. '카테고리' 컬럼에 '상세' 값이 있는지")
        log("  2. '상품 코드'가 6자리 숫자인지")
        log("  3. 'Video ID'가 유효한 유튜브 ID인지")
        sys.exit(1)
    
    # 생성된 파일 목록 출력
    log("\n📁 생성된 파일:")
    for code in sorted(grouped_data.keys()):
        log(f"  - {code}.html")

if __name__ == '__main__':
    build_site()
