import os
from datetime import datetime

import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from repository import init_db, add_favorite, get_favorites, delete_favorite


load_dotenv()
init_db()

try:
    AUTH_KEY = st.secrets["KRX_AUTH_KEY"]
except Exception:
    AUTH_KEY = os.getenv("KRX_AUTH_KEY")


def get_krx_daily_data(bas_dd):
    url = "http://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd"

    headers = {
        "AUTH_KEY": AUTH_KEY
    }

    params = {
        "basDd": bas_dd
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()

    if "OutBlock_1" not in data:
        return pd.DataFrame()

    return pd.DataFrame(data["OutBlock_1"])


def clean_columns(df):
    if df.empty:
        return df

    selected_cols = [
        "BAS_DD",
        "ISU_CD",
        "ISU_NM",
        "MKT_NM",
        "TDD_CLSPRC",
        "CMPPREVDD_PRC",
        "FLUC_RT",
        "TDD_OPNPRC",
        "TDD_HGPRC",
        "TDD_LWPRC",
        "ACC_TRDVOL",
        "ACC_TRDVAL",
        "MKTCAP",
        "LIST_SHRS"
    ]

    df = df[selected_cols].copy()

    df = df.rename(columns={
        "BAS_DD": "기준일",
        "ISU_CD": "종목코드",
        "ISU_NM": "종목명",
        "MKT_NM": "시장",
        "TDD_CLSPRC": "종가",
        "CMPPREVDD_PRC": "전일대비",
        "FLUC_RT": "등락률",
        "TDD_OPNPRC": "시가",
        "TDD_HGPRC": "고가",
        "TDD_LWPRC": "저가",
        "ACC_TRDVOL": "거래량",
        "ACC_TRDVAL": "거래대금",
        "MKTCAP": "시가총액",
        "LIST_SHRS": "상장주식수"
    })

    number_cols = [
        "종가",
        "전일대비",
        "시가",
        "고가",
        "저가",
        "거래량",
        "거래대금",
        "시가총액",
        "상장주식수"
    ]

    for col in number_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").map(
                lambda x: f"{int(x):,}" if pd.notna(x) else ""
            )

    if "등락률" in df.columns:
        df["등락률"] = pd.to_numeric(df["등락률"], errors="coerce").map(
            lambda x: f"{x:.2f}%" if pd.notna(x) else ""
        )

    return df


def get_favorite_data(df, user_id):
    favorites = get_favorites(user_id)

    if not favorites:
        return pd.DataFrame()

    favorite_codes = [code for code, name, market in favorites]
    result_df = df[df["ISU_CD"].isin(favorite_codes)]

    return clean_columns(result_df)


st.set_page_config(
    page_title="KRX 관심종목 조회",
    layout="wide"
)

st.title("KRX 관심종목 조회")
st.caption("사용자별 관심종목을 저장하고, 선택한 날짜의 일별 데이터를 CSV로 다운로드합니다.")

# =========================
# 상단 설정 영역
# =========================

col_user, col_date, col_load = st.columns([1.2, 1.2, 0.8])

with col_user:
    user_id = st.text_input("사용자 ID", placeholder="예: user01")

with col_date:
    selected_date = st.date_input(
        "조회 날짜",
        value=datetime.today(),
        label_visibility="visible"
    )
    bas_dd = selected_date.strftime("%Y%m%d")

with col_load:
    st.write("")
    st.write("")
    load_clicked = st.button("KRX 데이터 불러오기", use_container_width=True)

if not user_id:
    st.warning("사용자 ID를 입력해 주세요.")
    st.stop()

if load_clicked:
    try:
        df = get_krx_daily_data(bas_dd)

        if df.empty:
            st.warning("데이터가 없습니다. 휴장일이거나 API 응답이 비어 있을 수 있습니다.")
        else:
            st.session_state["krx_df"] = df
            st.success(f"{bas_dd} 기준 {len(df)}개 종목 데이터를 불러왔습니다.")

    except Exception as e:
        st.error(f"KRX 데이터 호출 실패: {e}")

if "krx_df" not in st.session_state:
    st.info("조회 날짜를 선택한 뒤 KRX 데이터를 불러와 주세요.")
    st.stop()

df = st.session_state["krx_df"]

st.divider()

# =========================
# 종목 검색 영역
# =========================

st.subheader("종목 검색")

keyword_col, guide_col = st.columns([2, 1])

with keyword_col:
    keyword = st.text_input(
        "종목명 또는 종목코드",
        placeholder="예: 삼성전자, 005930, NAVER",
        label_visibility="collapsed"
    )

with guide_col:
    st.caption("검색 결과의 ➕ 버튼을 누르면 관심종목에 추가됩니다.")

if keyword:
    search_df = df[
        df["ISU_NM"].str.contains(keyword, case=False, na=False)
        | df["ISU_CD"].str.contains(keyword, na=False)
    ]

    if search_df.empty:
        st.warning("검색 결과가 없습니다.")
    else:
        st.caption(f"검색 결과 {len(search_df)}개")

        header_cols = st.columns([1, 2, 1, 1, 0.4])
        header_cols[0].markdown("**종목코드**")
        header_cols[1].markdown("**종목명**")
        header_cols[2].markdown("**시장**")
        header_cols[3].markdown("**종가**")
        header_cols[4].markdown("**추가**")

        for _, row in search_df.head(20).iterrows():
            col1, col2, col3, col4, col5 = st.columns([1, 2, 1, 1, 0.4])

            col1.write(row["ISU_CD"])
            col2.write(row["ISU_NM"])
            col3.write(row["MKT_NM"])

            price = pd.to_numeric(row["TDD_CLSPRC"], errors="coerce")
            col4.write(f"{int(price):,}원" if pd.notna(price) else "-")

            if col5.button("➕", key=f"add_{user_id}_{row['ISU_CD']}"):
                added = add_favorite(
                    user_id,
                    row["ISU_CD"],
                    row["ISU_NM"],
                    row["MKT_NM"]
                )

                if added:
                    st.success(f"{row['ISU_NM']} 관심종목 추가 완료")
                    st.rerun()
                else:
                    st.warning("이미 관심종목에 등록된 종목입니다.")

st.divider()

# =========================
# 관심종목 통합 표
# =========================

st.subheader("관심종목 데이터")

favorite_result_df = get_favorite_data(df, user_id)

if favorite_result_df.empty:
    st.info("관심종목이 없습니다. 위 검색창에서 종목을 추가해 주세요.")
else:
    st.caption("➖ 버튼을 누르면 관심종목에서 삭제됩니다.")

    header_cols = st.columns([1, 1.6, 0.8, 1, 1, 1, 1, 1, 1.2, 0.4])
    header_cols[0].markdown("**종목코드**")
    header_cols[1].markdown("**종목명**")
    header_cols[2].markdown("**시장**")
    header_cols[3].markdown("**종가**")
    header_cols[4].markdown("**전일대비**")
    header_cols[5].markdown("**등락률**")
    header_cols[6].markdown("**거래량**")
    header_cols[7].markdown("**거래대금**")
    header_cols[8].markdown("**시가총액**")
    header_cols[9].markdown("**삭제**")

    for _, row in favorite_result_df.iterrows():
        col1, col2, col3, col4, col5, col6, col7, col8, col9, col10 = st.columns(
            [1, 1.6, 0.8, 1, 1, 1, 1, 1, 1.2, 0.4]
        )

        col1.write(row["종목코드"])
        col2.write(row["종목명"])
        col3.write(row["시장"])
        col4.write(row["종가"])
        col5.write(row["전일대비"])
        col6.write(row["등락률"])
        col7.write(row["거래량"])
        col8.write(row["거래대금"])
        col9.write(row["시가총액"])

        if col10.button("➖", key=f"delete_{user_id}_{row['종목코드']}"):
            delete_favorite(user_id, row["종목코드"])
            st.warning(f"{row['종목명']} 관심종목 삭제 완료")
            st.rerun()

    st.divider()

    csv_data = favorite_result_df.to_csv(index=False).encode("utf-8-sig")

    file_name = f"krx_favorites_{user_id}_{bas_dd}_{datetime.now().strftime('%H%M%S')}.csv"

    st.download_button(
        label="CSV 다운로드",
        data=csv_data,
        file_name=file_name,
        mime="text/csv",
        use_container_width=True
    )