import json
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import streamlit as st
import plotly.express as px
from streamlit_option_menu import option_menu
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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
    choice = option_menu("Menu", ["EDA", "시연", "데이터"],
                         icons=['kanban','bi bi-pin-map-fill','bi bi-database-fill'],
                         menu_icon="app-indicator", default_index=0,
                         styles={
        "container": {"padding": "4!important", "background-color": "#D9D9D9"},
        "icon": {"color": "black", "font-size": "25px"},
        "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#fafafa"},
        "nav-link-selected": {"background-color": "#08c7b4"},
    }
    )

# 페이지 전환 로직
#인프라 부족 현황과 반려동물 수
if choice == "EDA":
    st.title("EDA")
    # 인구수 막대그래프
    st.subheader("서울 각 구별 인구수")
    population_df_sorted = population_df.sort_values(by='인구수', ascending=False)
    population_bar = px.bar(
        population_df,
        x='동별',
        y='인구수',
        labels={'동별': '자치구', '인구수': '인구 수'},
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
    st.subheader("서울 구별 인구 3D 지도")
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
                zoom=9,
                pitch=45,  # 지도 기울기 설정
                bearing=0,  # 회전 각도 설정
            ),
            tooltip={
                "html": "<b>자치구:</b> {sggnm}<br>"
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
                zoom=9,
                pitch=45,  # 지도 기울기 설정
                bearing=0,  # 회전 각도 설정
            ),
            tooltip={
                "html": "<b>자치구:</b> {sggnm}<br>"
                        "<b>인구수:</b> {인구수}<br>",
                "style": {"backgroundColor": "darkorange", "color": "white"},
            },
            map_style="light",
        )
        st.pydeck_chart(deck)

    # 반려동물 등록 시연1 막대그래프
    st.subheader("서울 각 구별 반려동물 등록 수")
    pets_df_sorted = pets_df.sort_values(by='등록수', ascending=False)
    pets_bar = px.bar(
        pets_df,
        x='sggnm',
        y='등록수',
        labels={'sggnm': '자치구', '등록수': '등록수'},
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
    st.subheader("서울 반려동물 등록 3D 지도")
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
                zoom=9,
                pitch=45,
                bearing=0,
            ),
            tooltip={
                "html": (
                    "<b>자치구:</b> {sggnm}<br>"
                    "<b>인구 수:</b> {인구수}<br>"
                ),
                "style": {
                    "backgroundColor": "darkorange",
                    "color": "white"
                },
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
                zoom=9,
                pitch=45,
                bearing=0,
            ),
            tooltip={
                "html": (
                    "<b>자치구:</b> {sggnm}<br>"
                    "<b>반려동물 등록 수:</b> {등록수}<br>"
                ),
                "style": {
                    "backgroundColor": "darkorange",
                    "color": "white"
                },
            },
            map_style="light",
        )
        st.pydeck_chart(petdeck)

    # 인프라개수 막대그래프
    st.subheader("서울 각 구별 인프라 수")
    infra_df_sorted = infra_count.sort_values(by='인프라개수', ascending=False)
    infra_bar = px.bar(
        infra_df_sorted,
        x='sggnm',
        y='인프라개수',
        labels={'sggnm': '자치구', '등록수': '등록 수'},
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
    st.subheader("등록수 대비 인프라 개수")
    petsbyinfra_sorted = seoul_gdf_merged.sort_values(by='인프라당반려동물', ascending=False)
    petsbyinfra_bar = px.bar(
        petsbyinfra_sorted,
        x='sggnm',
        y='인프라당반려동물',
        labels={'sggnm': '자치구', '등록수': '등록 수'},
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

    seoul_infrafig = px.pie(
        infra_df,
        values="count",
        names="카테고리2",
        color_discrete_sequence=[
            'rgb(68, 128, 63)',  # 첫 번째 색상
            'rgb(89, 168, 83)',  # 두 번째 색상
            'rgb(255, 139, 73)',  # 세 번째 색상
            'rgb(255, 205, 74)'  # 네 번째 색상
        ]
    )

    st.subheader("서울시 반려동물 관련 중분류 분포")
    st.plotly_chart(seoul_infrafig)

    # Plotly로 시각화
    # '카테고리2' 컬럼을 '중분류'로 이름 변경
    grouped = grouped.rename(columns={'카테고리2': '중분류'})

    # '중분류' 컬럼을 기준으로 그룹화 및 정렬
    category_order = grouped.groupby('중분류')['count'].sum().sort_values(ascending=False).index.tolist()
    st.subheader("서울시 구별 중분류 분포")

    seoul_gu_infrafig = px.bar(
        grouped,
        x="시군구 명칭",
        y="count",
        color="중분류",
        labels={"count": "개수", "시군구 명칭": "자치구"},
        color_discrete_sequence=[
            'rgb(68, 128, 63)',  # 첫 번째 색상
            'rgb(89, 168, 83)',  # 두 번째 색상
            'rgb(255, 139, 73)',  # 세 번째 색상
            'rgb(255, 205, 74)'  # 네 번째 색상
        ],
        barmode="group",  # 그룹으로 막대 그래프 표시
        category_orders={"중분류": category_order}  # 카테고리 정렬 적용
    )

    st.plotly_chart(seoul_gu_infrafig)
    # 인프라당 반려동물 비율이 높은 상위 2개의 구 선택 (비율이 높을수록 인프라 부족)
    top_2_cities_based_on_ratio = seoul_gdf_merged.nlargest(2, "인프라당반려동물")["sggnm"].tolist()

    # 인프라당 반려동물 비율이 낮은 하위 2개의 구 선택 (비율이 낮을수록 인프라 충분)
    bottom_2_cities_based_on_ratio = seoul_gdf_merged.nsmallest(2, "인프라당반려동물")["sggnm"].tolist()

    # 상위 및 하위 구를 하나의 리스트로 합침
    selected_cities_based_on_ratio = top_2_cities_based_on_ratio + bottom_2_cities_based_on_ratio

    # grouped 데이터프레임에서 선택된 구에 해당하는 데이터 필터링
    filtered_grouped_based_on_ratio = grouped[grouped["시군구 명칭"].isin(selected_cities_based_on_ratio)]

    # 2x2 서브플롯 생성, 각 셀의 타입을 'domain'으로 지정
    top_fig = make_subplots(
        rows=2, cols=2,
        specs=[[{'type': 'domain'}, {'type': 'domain'}],
               [{'type': 'domain'}, {'type': 'domain'}]],
        subplot_titles=selected_cities_based_on_ratio
    )
    st.subheader("")
    # 각 구별로 파이 차트 생성 및 추가
    row_col_positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
    for i, city in enumerate(selected_cities_based_on_ratio):
        # 각 구별로 데이터 필터링
        city_data = filtered_grouped_based_on_ratio[filtered_grouped_based_on_ratio["시군구 명칭"] == city]

        # 파이 차트 추가
        pie_chart = go.Pie(
            labels=city_data["중분류"],
            values=city_data["count"],
            name=city,
            hole=0.3,
            marker=dict(
                colors=[
                    'rgb(89, 168, 83)',  # 반려의료
                    'rgb(255, 205, 74)',  # 반려동물 서비스
                    'rgb(255, 139, 73)',  # 반려동반여행
                    'rgb(68, 128, 63)'  # 반려동식당카
                ]
            )
        )

        top_fig.add_trace(pie_chart, row=row_col_positions[i][0], col=row_col_positions[i][1])

    # 레이아웃 설정
    top_fig.update_layout(showlegend=True)
    st.subheader("인프라 부족한 지역과 많은 지역 인프라 비교")
    # Streamlit의 plotly_chart로 차트 표시
    st.plotly_chart(top_fig)


#인프라 분포 및 밀도 분석
elif choice == "시연":
    # GeoJSON 파일 로드 및 GeoDataFrame으로 변환
    seoul_geo_path = './resource/seoul_gu.geojson'
    seoul_gdf = gpd.read_file(seoul_geo_path)

    # 시설 데이터 로드
    facilities_df = pd.read_csv('./resource/seoul_pets.csv', encoding='utf-8')

    # 구별로 병합
    seoul_gu_gdf = seoul_gdf.dissolve(by='sggnm')

    # 병합된 GeoDataFrame을 GeoJSON 형식으로 변환
    seoul_gu_geojson = json.loads(seoul_gu_gdf.to_json())

    # 데이터프레임 생성 - 자치구만 포함
    gu_names = seoul_gu_gdf.index.tolist()
    seoul_info = pd.DataFrame({"gu_name": gu_names})

    # 각 구의 중심 좌표 계산
    seoul_gu_gdf['center'] = seoul_gu_gdf.geometry.centroid
    seoul_gu_gdf['center_lat'] = seoul_gu_gdf.center.y
    seoul_gu_gdf['center_lon'] = seoul_gu_gdf.center.x


    # 구별 고유한 색상 매핑 생성 (서울은 연두색으로 설정)
    def generate_colors(n):
        colors = ['rgb(210, 245, 115)'] * n  # 서울을 연두색으로 설정
        return colors


    colors = "generate_colors(len(gu_names))"
    seoul_info['color'] = colors

    marker_styles = {
        '동물병원': {'size': 10, 'color': '#4F77A3', 'symbol': 'circle'},  # 부드러운 파란색
        '동물약국': {'size': 10, 'color': '#6BBE72', 'symbol': 'circle'},  # 부드러운 초록색
        '카페': {'size': 10, 'color': '#D86B47', 'symbol': 'circle'},  # 부드러운 빨간색
        '식당': {'size': 10, 'color': '#E79A47', 'symbol': 'circle'},  # 부드러운 주황색
        '미용': {'size': 10, 'color': '#9B64B7', 'symbol': 'circle'},  # 부드러운 보라색
        '반려동물용품': {'size': 10, 'color': '#F19BC1', 'symbol': 'circle'},  # 부드러운 분홍색
        '위탁관리': {'size': 10, 'color': '#F1D354', 'symbol': 'circle'},  # 부드러운 노란색
        '미술관': {'size': 10, 'color': '#67C6C2', 'symbol': 'circle'},  # 부드러운 시안색
        '박물관': {'size': 10, 'color': '#C97EC9', 'symbol': 'circle'},  # 부드러운 마젠타색
        '문예회관': {'size': 10, 'color': '#A8A8A8', 'symbol': 'circle'},  # 부드러운 회색
        '여행지': {'size': 10, 'color': '#757575', 'symbol': 'circle'},  # 부드러운 검은색
        '펜션': {'size': 10, 'color': '#A66E44', 'symbol': 'circle'},  # 부드러운 갈색
        'default': {'size': 10, 'color': '#D0D0D0', 'symbol': 'circle'}  # 부드러운 회색
    }


    def create_map(center_lat=37.563383, center_lon=126.996039, zoom=10, selected_gu=None):
        # 기본 지도 생성 (구 경계)
        fig = px.choropleth_mapbox(
            seoul_info,
            geojson=seoul_gu_geojson,
            locations='gu_name',
            color='gu_name',
            color_discrete_map=dict(zip(seoul_info['gu_name'], seoul_info['color'])),
            mapbox_style="carto-positron",
            opacity=0.8
        )

        # 구별 시설 마커 추가
        if selected_gu is not None:
            mask = facilities_df['시군구 명칭'] == selected_gu
            points_df = facilities_df[mask]

            categories = points_df['카테고리3'].unique()

            for category in categories:
                category_points = points_df[points_df['카테고리3'] == category]
                marker_style = marker_styles.get(category, marker_styles['default'])

                fig.add_scattermapbox(
                    lat=category_points['위도'],
                    lon=category_points['경도'],
                    mode='markers',
                    marker=dict(
                        size=marker_style['size'],
                        symbol=marker_style['symbol'],  # 카테고리 기반 모양 설정
                        color=marker_style['color'],  # 카테고리 기반 색상 설정
                    ),
                    text=category_points['시설명'],
                    customdata=category_points[[
                        '도로명주소', '전화번호', '운영시간', '휴무일',
                        '주차 가능여부', '반려동물 동반 가능정보', '반려동물 전용 정보',
                        '입장 가능 동물 크기', '반려동물 제한사항', '장소(실내) 여부',
                        '애견 동반 추가 요금', '기본 정보_장소설명'
                    ]],
                    hovertemplate=(
                            "<b>%{text}</b><br><br>" +
                            "카테고리: " + category + "<br>" +
                            "주소: %{customdata[0]}<br>" +
                            "전화번호: %{customdata[1]}<br>" +
                            "운영시간: %{customdata[2]}<br>" +
                            "휴무일: %{customdata[3]}<br>" +
                            "주차 가능여부: %{customdata[4]}<br>" +
                            "반려동물 동반 가능정보: %{customdata[5]}<br>" +
                            "반려동물 전용 정보: %{customdata[6]}<br>" +
                            "입장 가능 동물 크기: %{customdata[7]}<br>" +
                            "반려동물 제한사항: %{customdata[8]}<br>" +
                            "장소: %{customdata[9]}<br>" +
                            "애견 동반 추가 요금: %{customdata[10]}<br>" +
                            "기본 정보: %{customdata[11]}<extra></extra>"
                    ),
                    name=category
                )

        # 구 선택이 없다면 서울 전체 지도, 구 선택이 있으면 선택된 구 중심에 맞춘 지도
        if selected_gu is not None:
            center_lat = seoul_gu_gdf.loc[selected_gu].center_lat
            center_lon = seoul_gu_gdf.loc[selected_gu].center_lon
            zoom = 11  # 선택된 구에 맞는 줌 레벨 설정
        else:
            center_lat = 37.563383  # 서울의 중앙 위도
            center_lon = 126.996039  # 서울의 중앙 경도
            zoom = 8  # 서울의 전체 지도를 보여주기 위한 줌 레벨

        fig.update_layout(
            mapbox=dict(
                center=dict(lat=center_lat, lon=center_lon),
                zoom=zoom
            ),
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )

        return fig


    # Streamlit 웹 애플리케이션
    st.title('서울 반려동물 동반 시설 지도')

    selected_gu = st.selectbox('구 선택', [None] + gu_names)

    # 지도 출력
    map = create_map(selected_gu=selected_gu)
    st.plotly_chart(map, use_container_width=True)

elif choice == "데이터":
    # 인구 데이터 확인
    st.subheader("인구 데이터 프레임")
    population_df = population_df.rename(columns={'동별': '자치구'})

    st.write(population_df)  # 데이터프레임의 상위 5개 행 출력
    # 반려동물등록 데이터 확인
    st.subheader("반려동물등록 데이터 프레임")
    pets_df = pets_df.rename(columns={'시군구': '자치구'})
    pets_df = pets_df.drop(columns="sggnm")
    st.write(pets_df)  # 데이터프레임의 상위 5개 행 출력
    # 구별 인프라 개수 데이터 확인
    st.subheader("구별 인프라 데이터 프레임")
    st.write(seoul_infra)  # 데이터프레임의 상위 5개 행 출력
    # 인구 데이터 확인
    st.subheader("결합 데이터 프레임")
    seoul_gdf_merged = seoul_gdf_merged.drop(columns=["시군구", "행정구역명"])

    new_order = [
        "sggnm",  "인구수", "등록수",
        "인프라개수", "정규화인구", "정규화반려동물", "인프라당반려동물",
        "geometry", "OBJECTID", "adm_nm", "adm_cd", "adm_cd2", "sgg",
        "sido", "sidonm",
    ]
    # 열 순서 변경
    seoul_gdf_merged = seoul_gdf_merged[new_order]
    pets_df = pets_df.rename(columns={'sggnm': '자치구'})

    st.write(seoul_gdf_merged)  # 데이터프레임의 상위 5개 행 출력

# 8. 인구수 및 반려동물 데이터 시각화 - 막대그래프


# population_bar.update_layout(
#     legend_font=dict(size=20),  # 범례 폰트 크기
#     xaxis_tickfont=dict(size=12),  # x축 눈금 폰트 크기
#     yaxis_tickfont=dict(size=12)  # y축 눈금 폰트 크기
# )
