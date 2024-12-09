import pandas as pd
import geopandas as gpd
import pydeck as pdk
import streamlit as st
import plotly.express as px
from streamlit_option_menu import option_menu


# 1. GeoJSON 파일 로드 및 GeoDataFrame으로 변환
seoul_geo_path = './resource/seoul_gu.geojson'
seoul_gdf = gpd.read_file(seoul_geo_path)

# 2. 구별로 병합
seoul_gu_gdf = seoul_gdf.dissolve(by='sggnm')

# 3. 인구,반려동물 데이터 로드
population_df = pd.read_csv('./resource/seoul_pop.csv', encoding='utf-8')
pets_df = pd.read_csv('./resource/pets_count.csv', encoding='utf-8')
# 인프라 개수 데이터 로드
infra_count = pd.read_csv("./resource/infra_count.csv", encoding='utf-8')
# 좌표 데이터 로드
seoul_infra = pd.read_csv('./resource/seoul_pets.csv', encoding="UTF-8")

base_color = 'rgb(255, 202, 67)'

# 4. 전처리 진행
# '동별'과 'sggnm'의 값을 맞추어 병합
population_df['동별'] = population_df['동별'].str.strip()  # 공백 제거 (필요한 경우)
seoul_gdf_merged = seoul_gu_gdf.join(population_df.set_index('동별'), on='sggnm')

pets_df['sggnm'] = pets_df['시군구'].str.strip()  # 공백 제거 (필요한 경우)
seoul_gdf_merged = pd.merge(seoul_gdf_merged, pets_df, on='sggnm', how='left')

infra_count['sggnm'] = infra_count['행정구역명'].str.strip()  # 공백 제거 (필요한 경우)
seoul_gdf_merged = pd.merge(seoul_gdf_merged, infra_count, on='sggnm', how='left')
# 5. Map view 설정
# 인구 최댓값 설정
max_population = population_df['인구수'].max()

seoul_gdf_merged['정규화인구'] = seoul_gdf_merged['인구수'] / seoul_gdf_merged['인구수'].max()
seoul_gdf_merged['정규화반려동물'] = seoul_gdf_merged['등록수'] / seoul_gdf_merged['등록수'].max()

seoul_gdf_merged['인프라당반려동물'] = seoul_gdf_merged['등록수'] / seoul_gdf_merged['인프라개수']


#인프라 전체 카테고리2 확인
infra = seoul_infra["카테고리2"].value_counts().sort_index()
infra_df = infra.reset_index()
infra_df = pd.DataFrame(infra_df)

#인프라 구별 카테고리2 확인

grouped = seoul_infra.groupby(["시군구 명칭", "카테고리2"]).size().reset_index(name="count")



with st.sidebar:
    choice = option_menu("Menu", ["서론", "본론", "결론", "데이터"],
                         icons=['house', 'kanban', 'bi bi-robot', 'bi bi-boxes'],
                         menu_icon="app-indicator", default_index=0,
                         styles={
        "container": {"padding": "4!important", "background-color": "#fafafa"},
        "icon": {"color": "black", "font-size": "25px"},
        "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#fafafa"},
        "nav-link-selected": {"background-color": "#08c7b4"},
    }
    )

# 페이지 전환 로직
#인프라 부족 현황과 반려동물 수
if choice == "서론":
    st.title("서론")
    st.write("서울시의 반려동물 수는 급증하고 있으며, 이에 따라 필요한 인프라의 확충이 요구되고 있습니다. 그러나 일부 지역에서는 인프라가 부족한 상황입니다. 본 연구는 서울시 내 반려동물 수와 인프라 분포를 비교하여 부족한 인프라가 어디에 필요한지 파악하는 것을 목표로 합니다.")
    # 인구수 막대그래프
    st.title("서울 각 구별 인구수")
    population_df_sorted = population_df.sort_values(by='인구수', ascending=False)
    population_bar = px.bar(
        population_df,
        x='동별',
        y='인구수',
        labels={'동별': '구 이름', '인구수': '인구 수'},
        text='인구수',  # 바에 표시될 텍스트
        template='plotly',
        category_orders={'동별': population_df_sorted['동별']},  # 높은 순으로 정렬된 '동별' 순서 적용
        color='인구수',  # 인구수에 따라 색상이 변하게 설정
        color_continuous_scale=[
            [0, 'rgb(28, 89, 60)'],  # 첫 색상 (기준 색상)
            [1, 'rgb(210, 245, 115)']  # 두 번째 색상 (변경될 색상)
        ]
    )
    population_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    st.plotly_chart(population_bar, use_container_width=True)
    # 7. Streamlit으로 시각화
    st.title("서울 구별 인구 3D 지도")
    onoff = st.toggle("인구수 3D")
    if onoff:
        # 6. 3D 효과를 위한 Pydeck 지도 설정 (구 선택 시 이름 표시)
        deck = pdk.Deck(
            layers=[
                pdk.Layer(
                    "GeoJsonLayer",
                    seoul_gdf_merged,
                    get_fill_color="""
                        [
                            (210 + (28 - 210) * 정규화인구), 
                            (245 + (89 - 245) * 정규화인구), 
                            (115 + (60 - 115) * 정규화인구)
                        ]
                    """,  # 인구수에 따라 색상 계산
                    get_elevation="정규화인구 * 1000",  # 인구수에 비례하여 높이 설정 (1000은 배율)
                    elevation_scale=5,  # 높이의 배율 설정
                    extruded=True,  # 3D 효과 활성화
                    auto_highlight=True,
                    highlight_color=[255, 202, 67, 150],
                    opacity=0.8,
                    pickable=True,  # 인터랙션 활성화
                ),
            ],
            initial_view_state=pdk.ViewState(
                latitude=37.563383,
                longitude=126.996039,
                zoom=10,
                pitch=45,  # 지도 기울기 설정
                bearing=0,  # 회전 각도 설정
            ),
            tooltip={
                "html": "<b>구 이름:</b> {sggnm}<br>"
                        "<b>인구수:</b> {인구수}<br>",
                "style": {"backgroundColor": "darkorange", "color": "white"},
            },
            map_style="light",
        )
        st.pydeck_chart(deck)
    else:
        # 6. 3D 효과를 위한 Pydeck 지도 설정 (구 선택 시 이름 표시)
        deck = pdk.Deck(
            layers=[
                pdk.Layer(
                    "GeoJsonLayer",
                    seoul_gdf_merged,
                    get_fill_color="""
                        [
                            (210 + (28 - 210) * 정규화인구), 
                            (245 + (89 - 245) * 정규화인구), 
                            (115 + (60 - 115) * 정규화인구)
                        ]
                    """,  # 인구수에 따라 색상 계산
                    get_elevation="정규화인구 * 1000",  # 인구수에 비례하여 높이 설정 (1000은 배율)
                    elevation_scale=5,  # 높이의 배율 설정
                    extruded=False,  # 3D 효과 활성화
                    auto_highlight=True,
                    highlight_color=[255, 202, 67, 255],
                    opacity=1,
                    pickable=True,  # 인터랙션 활성화
                ),
            ],
            initial_view_state=pdk.ViewState(
                latitude=37.563383,
                longitude=126.996039,
                zoom=10,
                pitch=45,  # 지도 기울기 설정
                bearing=0,  # 회전 각도 설정
            ),
            tooltip={
                "html": "<b>구 이름:</b> {sggnm}<br>"
                        "<b>인구수:</b> {인구수}<br>",
                "style": {"backgroundColor": "darkorange", "color": "white"},
            },
            map_style="light",
        )
        st.pydeck_chart(deck)

    # 반려동물 등록 데이터 막대그래프
    st.title("서울 각 구별 반려동물 등록 수")
    pets_df_sorted = pets_df.sort_values(by='등록수', ascending=False)
    pets_bar = px.bar(
        pets_df,
        x='sggnm',
        y='등록수',
        labels={'sggnm': '구 이름', '등록수': '등록수'},
        text='등록수',
        template='plotly_white',
        category_orders={'sggnm': pets_df_sorted['sggnm']},  # 높은 순으로 정렬된 'sggnm' 순서 적용
        color='등록수',  # 인구수에 따라 색상이 변하게 설정
        color_continuous_scale=[
            [0, 'rgb(28, 89, 60)'],  # 첫 색상 (기준 색상)
            [1, 'rgb(210, 245, 115)']  # 두 번째 색상 (변경될 색상)
        ]
    )
    pets_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    st.plotly_chart(pets_bar, use_container_width=True)
    st.title("서울 반려동물 등록 3D 지도")
    petonoff = st.toggle("반려동물 3D")
    if petonoff:
        petdeck = pdk.Deck(
            layers=[
                pdk.Layer(
                    "GeoJsonLayer",
                    seoul_gdf_merged,
                    get_fill_color="""
                        [
                            (210 + (28 - 210) * 정규화반려동물), 
                            (245 + (89 - 245) * 정규화반려동물), 
                            (115 + (60 - 115) * 정규화반려동물)
                        ]
                    """,  # 반려동물 등록 수에 따라 색상 계산
                    get_elevation="정규화반려동물 * 1000",  # 반려동물 등록 수에 비례하여 높이 설정 (1000은 배율)
                    elevation_scale=5,  # 높이의 배율 설정
                    extruded=True,  # 3D 효과 활성화
                    auto_highlight=True,
                    opacity=0.6,
                    pickable=True,  # 인터랙션 활성화
                    highlight_color=[255, 202, 67, 150],

                ),
            ],
            initial_view_state=pdk.ViewState(
                latitude=37.563383,
                longitude=126.996039,
                zoom=10,
                pitch=45,
                bearing=0,
            ),
            tooltip={
                "html": "<b>구 이름:</b> {sggnm}<br>"
                        "<b>반려동물 등록 수:</b> {등록수}<br>"
                        "<b>인프라당 반려동물:</b> {인프라당반려동물:.2f}",
                "style": {"backgroundColor": "darkorange", "color": "white"},
            },
            map_style="light",
        )
        st.pydeck_chart(petdeck)
    else:
        petdeck = pdk.Deck(
            layers=[
                pdk.Layer(
                    "GeoJsonLayer",
                    seoul_gdf_merged,
                    get_fill_color="""
                        [
                            (210 + (28 - 210) * 정규화반려동물), 
                            (245 + (89 - 245) * 정규화반려동물), 
                            (115 + (60 - 115) * 정규화반려동물)
                        ]
                    """,  # 반려동물 등록 수에 따라 색상 계산
                    get_elevation="정규화반려동물 * 1000",  # 반려동물 등록 수에 비례하여 높이 설정 (1000은 배율)
                    elevation_scale=5,  # 높이의 배율 설정
                    extruded=False,  # 3D 효과 활성화
                    auto_highlight=True,
                    highlight_color=[255, 202, 67, 50],
                    opacity=0.8,
                    pickable=True,  # 인터랙션 활성화

                ),
            ],
            initial_view_state=pdk.ViewState(
                latitude=37.563383,
                longitude=126.996039,
                zoom=10,
                pitch=45,
                bearing=0,
            ),
            tooltip={
                "html": "<b>구 이름:</b> {sggnm}<br>"
                        "<b>반려동물 등록 수:</b> {등록수}<br>"
                        "<b>인프라당 반려동물:</b> {인프라당반려동물:.2f}",
                "style": {"backgroundColor": "darkorange", "color": "white"},
            },
            map_style="light",
        )
        st.pydeck_chart(petdeck)

#인프라 분포 및 밀도 분석
elif choice == "본론":
    st.title("본론")
    st.write("서울시의 반려동물 수와 인프라 분포를 분석한 결과, 반려동물이 많은 지역에서 인프라가 부족한 것으로 나타났습니다. 특히 강남구와 송파구는 인프라가 잘 갖춰져 있지만, 도봉구와 동작구와 같은 지역에서는 추가적인 인프라가 필요합니다.")
    # 인프라개수 막대그래프
    st.title("서울 각 구별 인프라 수")
    infra_df_sorted = infra_count.sort_values(by='인프라개수', ascending=False)
    infra_bar = px.bar(
        infra_df_sorted,
        x='sggnm',
        y='인프라개수',
        labels={'sggnm': '구 이름', '등록수': '등록 수'},
        text='인프라개수',
        template='plotly_white',
        category_orders={'sggnm': infra_df_sorted['sggnm']},  # 높은 순으로 정렬된 'sggnm' 순서 적용
        color='인프라개수',  # 인구수에 따라 색상이 변하게 설정
        color_continuous_scale=[
            [0, 'rgb(28, 89, 60)'],  # 첫 색상 (기준 색상)
            [1, 'rgb(210, 245, 115)']  # 두 번째 색상 (변경될 색상)
        ]
    )
    infra_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    st.plotly_chart(infra_bar, use_container_width=True)

    # 등록수 대비 인프라개수 막대그래프
    st.title("등록수 대비 인프라 개수")
    st.text("값이 클수록 인프라에 비해 등록된 반려동물이 많으므로 부족하다고 판단할 수 있습니다.")
    petsbyinfra_sorted = seoul_gdf_merged.sort_values(by='인프라당반려동물', ascending=False)
    petsbyinfra_bar = px.bar(
        petsbyinfra_sorted,
        x='sggnm',
        y='인프라당반려동물',
        labels={'sggnm': '구 이름', '등록수': '등록 수'},
        text='인프라당반려동물',
        template='plotly_white',
        category_orders={'sggnm': petsbyinfra_sorted['sggnm']},  # 높은 순으로 정렬된 'sggnm' 순서 적용
        color='인프라당반려동물',  # 인구수에 따라 색상이 변하게 설정
        color_continuous_scale=[
            [0, 'rgb(28, 89, 60)'],  # 첫 색상 (기준 색상)
            [1, 'rgb(210, 245, 115)']  # 두 번째 색상 (변경될 색상)
        ]
    )
    petsbyinfra_bar.update_traces(texttemplate='%{text:.3s}', textposition='outside')
    st.plotly_chart(petsbyinfra_bar, use_container_width=True)

    # 카테고리 파이 그래프
    seoul_infrafig = px.pie(
        infra_df,
        values="count",
        names="카테고리2",
        title="반려동물 관련 카테고리 분포",
        color_discrete_sequence=px.colors.sequential.RdBu  # 색상 설정 (옵션)
    )

    st.title("반려동물 관련 카테고리 분포")
    st.plotly_chart(seoul_infrafig)

    # Plotly로 시각화
    category_order = grouped.groupby('카테고리2')['count'].sum().sort_values(ascending=False).index.tolist()

    seoul_gu_infrafig = px.bar(
        grouped,
        x="시군구 명칭",
        y="count",
        color="카테고리2",
        title="구별 카테고리2 분포 (카테고리 총 개수 기준 정렬)",
        labels={"count": "개수", "시군구 명칭": "구 이름"},
        color_discrete_sequence=px.colors.qualitative.Set3,  # 색상 조정
        barmode="group",  # 그룹으로 막대 그래프 표시
        category_orders={"카테고리2": category_order}  # 카테고리 정렬 적용
    )
    st.plotly_chart(seoul_gu_infrafig)

#필요한 인프라가 부족한 지역
elif choice == "결론":
    st.title("페이지 3")
    st.write("여기는 페이지 3의 내용입니다.")
elif choice == "데이터":
    # 인구 데이터 확인
    st.subheader("인구 데이터 프레임")
    st.write(population_df)  # 데이터프레임의 상위 5개 행 출력
    # 반려동물등록 데이터 확인
    st.subheader("반려동물등록 데이터 프레임")
    st.write(pets_df)  # 데이터프레임의 상위 5개 행 출력
    # 구별 인프라 개수 데이터 확인
    st.subheader("구별 인프라 개수 데이터 프레임")
    st.write(seoul_infra)  # 데이터프레임의 상위 5개 행 출력
    # 인구 데이터 확인
    st.subheader("결합 데이터 프레임")
    st.write(seoul_gdf_merged)  # 데이터프레임의 상위 5개 행 출력

# 8. 인구수 및 반려동물 데이터 시각화 - 막대그래프


# population_bar.update_layout(
#     legend_font=dict(size=20),  # 범례 폰트 크기
#     xaxis_tickfont=dict(size=12),  # x축 눈금 폰트 크기
#     yaxis_tickfont=dict(size=12)  # y축 눈금 폰트 크기
# )








