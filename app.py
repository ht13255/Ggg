import streamlit as st
import pandas as pd
import time
import gc
from pandas.errors import EmptyDataError, ParserError
from json import JSONDecodeError

st.set_page_config(page_title="파일 병합기 (자동 구분자 & 클린업)", layout="wide")
st.title("🚀 자동 구분자 CSV·JSON 병합기")

st.markdown("""
- CSV(.csv) / JSON(.json) 파일을 업로드하면 세로 방향으로 이어붙입니다.  
- CSV는 `sep=None, engine='python'`으로 자동으로 구분자를 감지합니다.  
- 다운로드 직후 내부 데이터를 삭제해 메모리/디스크 사용을 최소화합니다.
""")

# 파일 업로드
uploaded_files = st.file_uploader(
    "CSV/JSON 파일 선택 (여러 개 가능)",
    type=["csv", "json"],
    accept_multiple_files=True
)

def read_file(file):
    """
    CSV는 자동 구분자(snip)로, JSON은 ndjson 우선 → 전체 배열 순으로 읽습니다.
    실패 시 None을 반환합니다.
    """
    name = file.name.lower()
    try:
        file.seek(0)
        if name.endswith(".csv"):
            # 자동 구분자 추론
            return pd.read_csv(file, sep=None, engine='python', low_memory=False)
        else:
            # JSON 읽기
            try:
                return pd.read_json(file, lines=True)
            except ValueError:
                file.seek(0)
                return pd.read_json(file)
    except (EmptyDataError, ParserError) as e:
        st.warning(f"⚠️ '{file.name}' 읽기 오류: {e}")
    except UnicodeDecodeError:
        st.warning(f"⚠️ '{file.name}' 인코딩 오류로 읽을 수 없습니다.")
    except JSONDecodeError as e:
        st.warning(f"⚠️ '{file.name}' JSON 구조 오류: {e}")
    except MemoryError:
        st.error(f"❌ '{file.name}' 메모리 부족으로 읽기 실패")
    except Exception as e:
        st.error(f"❌ '{file.name}' 알 수 없는 오류: {e}")
    return None

if uploaded_files:
    dfs = []
    total_rows = 0
    progress = st.progress(0)
    start_time = time.time()

    # 1) 파일별로 읽기
    for idx, file in enumerate(uploaded_files, 1):
        df = read_file(file)
        if df is not None and not df.empty:
            dfs.append(df)
            total_rows += len(df)
        elif df is not None:
            st.warning(f"⚠️ '{file.name}'에서 읽은 데이터가 없습니다.")
        progress.progress(idx / len(uploaded_files))

    if not dfs:
        st.error("❌ 유효한 데이터를 읽어들인 파일이 없습니다.")
        st.stop()

    # 2) 병합
    try:
        merged = pd.concat(dfs, ignore_index=True)
    except MemoryError:
        st.error("❌ 병합 중 메모리 부족이 발생했습니다.")
        st.stop()
    except Exception as e:
        st.error(f"❌ 병합 중 알 수 없는 오류: {e}")
        st.stop()

    elapsed = time.time() - start_time
    st.success(f"✅ {len(dfs)}개 파일 · {total_rows}행 병합 완료! ({elapsed:.2f}s)")
    st.dataframe(merged.head(100), use_container_width=True)

    # 3) 다운로드 & 클린업
    to_download = st.radio("다운로드 형식 선택", ["CSV", "JSON"], index=0)
    if to_download == "CSV":
        data = merged.to_csv(index=False).encode("utf-8")
        mime, fname = "text/csv", "merged.csv"
    else:
        data = merged.to_json(orient="records", force_ascii=False).encode("utf-8")
        mime, fname = "application/json", "merged.json"

    if st.download_button("🔽 파일 다운로드", data=data, file_name=fname, mime=mime):
        # 다운로드가 트리거되면 메모리/변수 정리
        del merged
        dfs.clear()
        gc.collect()
        st.info("🗑️ 임시 데이터가 삭제되어 저장 공간이 확보되었습니다.")
else:
    st.info("좌측 위 ‘Browse files’ 버튼을 눌러 CSV 또는 JSON 파일을 업로드하세요.")