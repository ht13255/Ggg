import streamlit as st
import pandas as pd
import time
import json
from pandas.errors import EmptyDataError, ParserError
from json import JSONDecodeError

st.set_page_config(page_title="파일 병합기 (CSV/JSON)", layout="wide")
st.title("🚀 초고속 CSV·JSON 병합기 (강화된 오류 처리)")

st.markdown("""
- CSV(.csv) / JSON(.json) 파일을 한 번에 업로드해 세로 방향으로 이어붙입니다.  
- 각종 인코딩·형식·메모리 오류를 최대한 잡아냅니다.
""")

# 1) 구분자 설정
delimiter = st.text_input("CSV 구분자", value=",", max_chars=1)

# 2) 파일 업로드
uploaded_files = st.file_uploader(
    "CSV/JSON 파일 선택 (여러 개 가능)",
    type=["csv", "json"],
    accept_multiple_files=True
)

def read_file(file, delimiter):
    """
    파일 종류에 따라 DataFrame으로 읽어오는 함수.
    오류 발생 시 None 리턴 + 메시지 기록.
    """
    name = file.name.lower()
    try:
        # 리셋
        file.seek(0)
        if name.endswith(".csv"):
            # CSV 읽기
            try:
                return pd.read_csv(file, delimiter=delimiter, low_memory=False)
            except EmptyDataError:
                st.warning(f"⚠️ '{file.name}'가 비어있습니다. (EmptyDataError)")
            except ParserError as e:
                st.warning(f"⚠️ '{file.name}' 구문 오류: {e}")
            except UnicodeDecodeError:
                # 다른 인코딩 시도
                file.seek(0)
                try:
                    return pd.read_csv(file, delimiter=delimiter, encoding='latin1', low_memory=False)
                except Exception as e2:
                    st.warning(f"⚠️ '{file.name}' 인코딩 오류 (utf-8/latin1 모두 실패): {e2}")
        else:
            # JSON 읽기 (NDJSON 우선 → 전체 배열)
            try:
                return pd.read_json(file, lines=True)
            except ValueError:
                file.seek(0)
                try:
                    return pd.read_json(file)
                except JSONDecodeError as e:
                    st.warning(f"⚠️ '{file.name}' JSON 구조 오류: {e}")
                except Exception as e2:
                    st.warning(f"⚠️ '{file.name}' JSON 읽기 실패: {e2}")
    except MemoryError:
        st.error(f"❌ '{file.name}' 메모리 부족으로 읽을 수 없습니다.")
    except Exception as e:
        st.error(f"❌ '{file.name}' 알 수 없는 오류: {e}")
    return None

if uploaded_files:
    dfs = []
    total_rows = 0
    errors = []
    progress = st.progress(0)
    start_time = time.time()

    # 3) 파일별로 읽기
    for idx, file in enumerate(uploaded_files, 1):
        # 파일 크기 제한 예시 (100MB)
        try:
            size_mb = file.size / (1024*1024)
            if size_mb > 100:
                st.warning(f"⚠️ '{file.name}' 용량이 {size_mb:.1f}MB로 큽니다. 읽기 실패 가능성이 있습니다.")
        except Exception:
            pass

        df = read_file(file, delimiter)
        if df is not None:
            n = len(df)
            if n == 0:
                st.warning(f"⚠️ '{file.name}'에서 읽어온 데이터가 없습니다.")
            else:
                dfs.append(df)
                total_rows += n
        progress.progress(idx / len(uploaded_files))

    # 4) 병합
    if dfs:
        try:
            merged = pd.concat(dfs, ignore_index=True)
            elapsed = time.time() - start_time
            st.success(f"✅ {len(dfs)}개 파일 · {total_rows}행 병합 완료! ({elapsed:.2f}s)")
            st.dataframe(merged.head(100), use_container_width=True)
        except MemoryError:
            st.error("❌ 모든 데이터를 한 번에 병합하는 과정에서 메모리 부족이 발생했습니다.")
            st.stop()
        except Exception as e:
            st.error(f"❌ 병합 중 알 수 없는 오류: {e}")
            st.stop()

        # 5) 다운로드 옵션
        to_download = st.radio("다운로드 형식 선택", ["CSV", "JSON"])
        try:
            if to_download == "CSV":
                data = merged.to_csv(index=False).encode("utf-8")
                mime = "text/csv"
                fname = "merged.csv"
            else:
                data = merged.to_json(orient="records", force_ascii=False).encode("utf-8")
                mime = "application/json"
                fname = "merged.json"

            st.download_button(
                label="🔽 파일 다운로드",
                data=data,
                file_name=fname,
                mime=mime
            )
        except Exception as e:
            st.error(f"❌ 다운로드 준비 중 오류: {e}")
    else:
        st.error("❌ 읽어들인 유효한 데이터가 없어 병합을 수행할 수 없습니다.")
else:
    st.info("좌측 위 ‘Browse files’ 버튼을 눌러 CSV 또는 JSON 파일을 업로드하세요.")
