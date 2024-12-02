import json
import pandas as pd
import geopandas as gpd
import plotly.express as px
import streamlit as st
import colorsys

# GeoJSON 파일 로드 및 GeoDataFrame으로 변환
seoul_geo_path = './resource/hangjeongdong_서울특별시.geojson'
seoul_gdf = gpd.read_file(seoul_geo_path)    

# 시설 데이터 로드
facilities_df = pd.read_csv('./resource/서울반려동물동반.csv', encoding='utf-8')

# 구별로 병합
seoul_gu_gdf = seoul_gdf.dissolve(by='sggnm')

# 병합된 GeoDataFrame을 GeoJSON 형식으로 변환
seoul_gu_geojson = json.loads(seoul_gu_gdf.to_json())

# 데이터프레임 생성 - 구 이름만 포함
gu_names = seoul_gu_gdf.index.tolist()
seoul_info = pd.DataFrame({"gu_name": gu_names})

# 각 구의 중심 좌표 계산
seoul_gu_gdf['center'] = seoul_gu_gdf.geometry.centroid
seoul_gu_gdf['center_lat'] = seoul_gu_gdf.center.y
seoul_gu_gdf['center_lon'] = seoul_gu_gdf.center.x


# 구별 고유한 색상 매핑 생성
def generate_colors(n):
    colors = []
    for i in range(n):
        hue = i / n
        saturation = 0.5
        value = 0.95
        rgb = colorsys.hsv_to_rgb(hue, saturation, value)
        colors.append('rgb(255, 255, 255)')  # Placeholder color, replace with dynamic if needed
    return colors


colors = generate_colors(len(gu_names))
seoul_info['color'] = colors

# 마커 스타일 지정 (이미지 URL 포함)
marker_styles = {
    '동물병원': {'image': 'url_to_pharmacy_image.png', 'size': 10},
    '동물약국': {'image': 'url_to_pharmacy_image.png', 'size': 10},
    '카페': {'image': 'url_to_cafe_image.png', 'size': 10},
    '식당': {'image': 'url_to_restaurant_image.png', 'size': 10},
    '미용': {'image': 'url_to_scissors_image.png', 'size': 10},
    '반려동물용품': {'image': 'url_to_shop_image.png', 'size': 10},
    '위탁관리': {'image': 'url_to_home_image.png', 'size': 10},
    '미술관': {'image': 'url_to_art_gallery_image.png', 'size': 10},
    '박물관': {'image': 'url_to_museum_image.png', 'size': 10},
    '문예회관': {'image': 'url_to_theatre_image.png', 'size': 10},
    '여행지': {'image': 'url_to_attraction_image.png', 'size': 10},
    '펜션': {'image': 'url_to_lodging_image.png', 'size': 10},
    'default': {'image': 'url_to_default_image.png', 'size': 10}
}


def create_map(center_lat=37.563383, center_lon=126.996039, zoom=10, selected_gu=None):
    # 기본 지도 생성 (구 경계)
    fig = px.choropleth_mapbox(
        seoul_info,
        geojson=seoul_gu_geojson,
        locations='gu_name',
        color='gu_name',
        color_discrete_map=dict(zip(seoul_info['gu_name'], seoul_info['color'])),
        mapbox_style="carto-darkmatter",
        opacity=0.5
    )

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
                    symbol='circle',  # 기본 모양으로 설정
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

if selected_gu is not None:
    center_lat = seoul_gu_gdf.loc[selected_gu].center_lat
    center_lon = seoul_gu_gdf.loc[selected_gu].center_lon
    map = create_map(center_lat=center_lat, center_lon=center_lon, zoom=12, selected_gu=selected_gu)
else:
    map = create_map()

st.plotly_chart(map, use_container_width=True)
