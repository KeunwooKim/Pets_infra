import pandas as pd
import geopandas as gpd
import pydeck as pdk
import streamlit as st
import plotly.express as px


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

# 인구 데이터 확인
st.subheader("인구 데이터 프레임")
st.write(population_df.head())  # 데이터프레임의 상위 5개 행 출력
# 반려동물등록 데이터 확인
st.subheader("반려동물등록 데이터 프레임")
st.write(pets_df.head())  # 데이터프레임의 상위 5개 행 출력
# 구별 인프라 개수 데이터 확인
st.subheader("구별 인프라 개수 데이터 프레임")
st.write(infra_count.head())  # 데이터프레임의 상위 5개 행 출력

# 4. 인구 데이터 병합
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

seoul_gdf_merged['반려동물등록률'] = (seoul_gdf_merged['등록수'] / seoul_gdf_merged['인구수'])*100
seoul_gdf_merged['인프라당반려동물'] = seoul_gdf_merged['등록수'] / seoul_gdf_merged['인프라개수']

# 인구 데이터 확인
st.subheader("결합 데이터 프레임")
st.write(seoul_gdf_merged)  # 데이터프레임의 상위 5개 행 출력

# 6. 3D 효과를 위한 Pydeck 지도 설정
# 3D 효과를 위한 Pydeck 지도 설정
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
            elevation_scale=10,  # 높이의 배율 설정
            extruded=True,  # 3D 효과 활성화
            auto_highlight=True,
            opacity=0.6,
            line_width_min_pixels=1,  # 경계선 두께
            get_line_color=[0, 0, 0],  # 경계선 색상
            line_width_scale=10,  # 경계선의 두께 강조
            pickable=True,
        ),
        # 텍스트 레이어 추가: 각 구의 이름을 표시
        pdk.Layer(
            "TextLayer",
            seoul_gdf_merged,
            get_position=["properties.lon", "properties.lat"],  # 경도, 위도 값 (추가로 설정해야 할 수 있음)
            get_text="sggnm",  # 구 이름을 텍스트로 표시
            get_size=30,  # 텍스트 크기
            get_color=[255, 255, 255],  # 텍스트 색상
            get_text_anchor="'middle'",  # 텍스트 정렬
            pickable=True  # 텍스트 클릭 가능
        ),
    ],
    initial_view_state=pdk.ViewState(
        latitude=37.563383,
        longitude=126.996039,
        zoom=10,
        pitch=45,  # 지도 기울기 설정
        bearing=0,  # 회전 각도 설정
    ),
    map_style="light",
)

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
            """,  # 인구수에 따라 색상 계산
            get_elevation="정규화반려동물 * 1000",  # 인구수에 비례하여 높이 설정 (1000은 배율)
            elevation_scale=10,  # 높이의 배율 설정
            extruded=True,  # 3D 효과 활성화
            auto_highlight=True,
            opacity=0.6,
            line_width_min_pixels=1,  # 경계선 두께
            get_line_color=[0, 0, 0],  # 경계선 색상
            line_width_scale=10,  # 경계선의 두께 강조
            pickable=True,
        ),
        # 텍스트 레이어 추가: 각 구의 이름을 표시
        pdk.Layer(
            "TextLayer",
            seoul_gdf_merged,
            get_position=["properties.lon", "properties.lat"],
            get_text="properties.sggnm",  # 구 이름을 텍스트로 표시
            get_size=30,
            get_color=[255, 255, 255],
            get_text_anchor="'middle'",
            pickable=True
        ),
    ],
    initial_view_state=pdk.ViewState(
        latitude=37.563383,
        longitude=126.996039,
        zoom=10,
        pitch=45,
        bearing=0,
    ),
    map_style="light",
)
# 8. 인구수 및 반려동물 데이터 시각화 - 막대그래프

# 인구수 막대그래프
st.title("서울 각 구별 인구수")
population_df_sorted = population_df.sort_values(by='인구수', ascending=False)
population_bar = px.bar(
    population_df,
    x='동별',
    y='인구수',
    labels={'동별': '구 이름', '인구수': '인구 수'},
    text='인구수',  # 바에 표시될 텍스트
    template='plotly_white',
    category_orders = {'동별': population_df_sorted['동별']}  # 높은 순으로 정렬된 '동별' 순서 적용

)
population_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
st.plotly_chart(population_bar, use_container_width=True)

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
    category_orders={'sggnm': pets_df_sorted['sggnm']}  # 높은 순으로 정렬된 'sggnm' 순서 적용

)
pets_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
st.plotly_chart(pets_bar, use_container_width=True)

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
    category_orders={'sggnm': infra_df_sorted['sggnm']}  # 높은 순으로 정렬된 'sggnm' 순서 적용

)
infra_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
st.plotly_chart(infra_bar, use_container_width=True)

# 인구수 대비 반려동물 등록률 막대그래프
st.title("반료동물 등록률")
st.text("특정 지역의 반려동물 등록 수가 인구에 비해 낮다면 반려동물 관심도가 낮거나 등록 홍보가 부족한 지역일 가능성이 높습니다.")
popbypets_sorted = seoul_gdf_merged.sort_values(by='반려동물등록률', ascending=True)
popbypets_bar = px.bar(
    popbypets_sorted,
    x='sggnm',
    y='반려동물등록률',
    labels={'sggnm': '구 이름', '등록수': '등록 수'},
    text='반려동물등록률',
    template='plotly_white',
    category_orders={'sggnm': popbypets_sorted['sggnm']}  # 높은 순으로 정렬된 'sggnm' 순서 적용

)
popbypets_bar.update_traces(texttemplate='%{text:.2s}', textposition='outside')
st.plotly_chart(popbypets_bar, use_container_width=True)

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
    category_orders={'sggnm': petsbyinfra_sorted['sggnm']}  # 높은 순으로 정렬된 'sggnm' 순서 적용

)
petsbyinfra_bar.update_traces(texttemplate='%{text:.3s}', textposition='outside')
st.plotly_chart(petsbyinfra_bar, use_container_width=True)

# 7. Streamlit으로 시각화
st.title("서울 구별 인구 3D 지도")
st.pydeck_chart(deck)
st.title("서울 반려동물 등록 3D 지도")
st.pydeck_chart(petdeck)
