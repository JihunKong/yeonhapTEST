import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
import streamlit_authenticator as stauth
from dotenv import load_dotenv
import yaml
from yaml.loader import SafeLoader

# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="모의고사 자가채점 시스템",
    page_icon="📝",
    layout="wide"
)

# 인증 설정
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# 세션 상태 초기화
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if 'name' not in st.session_state:
    st.session_state['name'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# 인증
try:
    name, authentication_status, username = authenticator.login('로그인', 'main')
    
    if authentication_status:
        st.success(f"환영합니다 {name}님!")
        
        # 사이드바
        authenticator.logout('로그아웃', 'sidebar')
        
        # 제목
        st.title(f"📝 모의고사 자가채점 시스템 - {name}님 환영합니다")
        
        # 데이터 파일 경로
        ANSWERS_FILE = "data/answers.csv"
        RESPONSES_FILE = "data/responses.csv"
        
        # 데이터 파일이 없으면 생성
        def initialize_data_files():
            if not os.path.exists(ANSWERS_FILE):
                pd.DataFrame({
                    '회차': [],
                    '과목': [],
                    '문항번호': [],
                    '정답': []
                }).to_csv(ANSWERS_FILE, index=False)
            
            if not os.path.exists(RESPONSES_FILE):
                pd.DataFrame({
                    '학생ID': [],
                    '회차': [],
                    '과목': [],
                    '문항번호': [],
                    '입력답': []
                }).to_csv(RESPONSES_FILE, index=False)
        
        initialize_data_files()
        
        # 메인 컨텐츠
        if username == 'teacher':
            st.header("교사용 관리")
            
            # 탭 생성
            tab1, tab2, tab3 = st.tabs(["정답 입력", "채점 결과", "통계 분석"])
            
            with tab1:
                # 정답 입력
                st.subheader("정답 입력")
                exam_round = st.selectbox("모의고사 회차를 선택하세요", ["1차", "2차", "3차", "4차"])
                subject = st.selectbox(
                    "과목을 선택하세요",
                    ["국어", "수학", "영어", "한국사", "탐구1", "탐구2"]
                )
                
                num_questions = st.number_input("문항 수를 입력하세요", min_value=1, max_value=50, value=20)
                
                answers = []
                for i in range(num_questions):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"{i+1}번")
                    with col2:
                        answer = st.text_input(f"정답", key=f"q_{i}")
                        answers.append(answer)
                
                if st.button("정답 저장"):
                    # 정답 저장
                    answers_df = pd.read_csv(ANSWERS_FILE)
                    for i, answer in enumerate(answers):
                        new_row = {
                            '회차': exam_round,
                            '과목': subject,
                            '문항번호': i+1,
                            '정답': answer
                        }
                        answers_df = pd.concat([answers_df, pd.DataFrame([new_row])], ignore_index=True)
                    answers_df.to_csv(ANSWERS_FILE, index=False)
                    st.success("정답이 저장되었습니다!")
            
            with tab2:
                # 채점 결과 확인
                st.subheader("채점 결과 확인")
                if os.path.exists(RESPONSES_FILE):
                    responses_df = pd.read_csv(RESPONSES_FILE)
                    answers_df = pd.read_csv(ANSWERS_FILE)
                    
                    selected_round = st.selectbox("확인할 회차를 선택하세요", responses_df['회차'].unique())
                    selected_subject = st.selectbox("확인할 과목을 선택하세요", responses_df['과목'].unique())
                    
                    if st.button("결과 확인"):
                        filtered_responses = responses_df[
                            (responses_df['회차'] == selected_round) & 
                            (responses_df['과목'] == selected_subject)
                        ]
                        
                        filtered_answers = answers_df[
                            (answers_df['회차'] == selected_round) & 
                            (answers_df['과목'] == selected_subject)
                        ]
                        
                        # 채점 결과 계산
                        results = []
                        for student_id in filtered_responses['학생ID'].unique():
                            student_responses = filtered_responses[filtered_responses['학생ID'] == student_id]
                            correct_count = 0
                            
                            for _, response in student_responses.iterrows():
                                correct_answer = filtered_answers[
                                    filtered_answers['문항번호'] == response['문항번호']
                                ]['정답'].iloc[0]
                                
                                if response['입력답'] == correct_answer:
                                    correct_count += 1
                            
                            results.append({
                                '학생ID': student_id,
                                '맞은 개수': correct_count,
                                '틀린 개수': len(student_responses) - correct_count,
                                '정답률': (correct_count/len(student_responses))*100
                            })
                        
                        results_df = pd.DataFrame(results)
                        st.dataframe(results_df)
                        
                        # 문항별 정답률 분석
                        st.subheader("문항별 정답률 분석")
                        question_stats = []
                        for q_num in range(1, len(filtered_answers) + 1):
                            question_responses = filtered_responses[filtered_responses['문항번호'] == q_num]
                            correct_count = 0
                            for _, response in question_responses.iterrows():
                                correct_answer = filtered_answers[
                                    filtered_answers['문항번호'] == response['문항번호']
                                ]['정답'].iloc[0]
                                if response['입력답'] == correct_answer:
                                    correct_count += 1
                        
                            question_stats.append({
                                '문항번호': q_num,
                                '정답률': (correct_count/len(question_responses))*100 if len(question_responses) > 0 else 0
                            })
                        
                        question_stats_df = pd.DataFrame(question_stats)
                        
                        # 문항별 정답률 시각화
                        fig = px.bar(question_stats_df, x='문항번호', y='정답률',
                                   title='문항별 정답률',
                                   labels={'문항번호': '문항 번호', '정답률': '정답률 (%)'})
                        st.plotly_chart(fig)
            
            with tab3:
                # 통계 분석
                st.subheader("통계 분석")
                if os.path.exists(RESPONSES_FILE):
                    responses_df = pd.read_csv(RESPONSES_FILE)
                    answers_df = pd.read_csv(ANSWERS_FILE)
                    
                    # 과목별 평균 정답률
                    st.subheader("과목별 평균 정답률")
                    subject_stats = []
                    for subject in responses_df['과목'].unique():
                        subject_responses = responses_df[responses_df['과목'] == subject]
                        subject_answers = answers_df[answers_df['과목'] == subject]
                        
                        correct_count = 0
                        total_count = 0
                        
                        for _, response in subject_responses.iterrows():
                            correct_answer = subject_answers[
                                subject_answers['문항번호'] == response['문항번호']
                            ]['정답'].iloc[0]
                            
                            if response['입력답'] == correct_answer:
                                correct_count += 1
                            total_count += 1
                        
                        subject_stats.append({
                            '과목': subject,
                            '평균정답률': (correct_count/total_count)*100 if total_count > 0 else 0
                        })
                    
                    subject_stats_df = pd.DataFrame(subject_stats)
                    
                    # 과목별 평균 정답률 시각화
                    fig = px.bar(subject_stats_df, x='과목', y='평균정답률',
                                title='과목별 평균 정답률',
                                labels={'과목': '과목', '평균정답률': '평균 정답률 (%)'})
                    st.plotly_chart(fig)
                    
                    # 회차별 추이 분석
                    st.subheader("회차별 추이 분석")
                    round_stats = []
                    for round_num in responses_df['회차'].unique():
                        round_responses = responses_df[responses_df['회차'] == round_num]
                        round_answers = answers_df[answers_df['회차'] == round_num]
                        
                        correct_count = 0
                        total_count = 0
                        
                        for _, response in round_responses.iterrows():
                            correct_answer = round_answers[
                                round_answers['문항번호'] == response['문항번호']
                            ]['정답'].iloc[0]
                            
                            if response['입력답'] == correct_answer:
                                correct_count += 1
                            total_count += 1
                        
                        round_stats.append({
                            '회차': round_num,
                            '평균정답률': (correct_count/total_count)*100 if total_count > 0 else 0
                        })
                    
                    round_stats_df = pd.DataFrame(round_stats)
                    
                    # 회차별 추이 시각화
                    fig = px.line(round_stats_df, x='회차', y='평균정답률',
                                 title='회차별 평균 정답률 추이',
                                 labels={'회차': '회차', '평균정답률': '평균 정답률 (%)'})
                    st.plotly_chart(fig)
        else:
            st.header("학생용 자가채점")
            
            # 학생 정보 입력
            student_id = username
            exam_round = st.selectbox("모의고사 회차를 선택하세요", ["1차", "2차", "3차", "4차"])
            
            # 과목 선택
            subject = st.selectbox(
                "과목을 선택하세요",
                ["국어", "수학", "영어", "한국사", "탐구1", "탐구2"]
            )
            
            # 답안 입력
            st.subheader("답안 입력")
            num_questions = 20  # 기본 문항 수
            answers = []
            
            for i in range(num_questions):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{i+1}번")
                with col2:
                    answer = st.text_input(f"답", key=f"q_{i}")
                    answers.append(answer)
            
            if st.button("제출"):
                # 답안 저장
                responses_df = pd.read_csv(RESPONSES_FILE)
                for i, answer in enumerate(answers):
                    new_row = {
                        '학생ID': student_id,
                        '회차': exam_round,
                        '과목': subject,
                        '문항번호': i+1,
                        '입력답': answer
                    }
                    responses_df = pd.concat([responses_df, pd.DataFrame([new_row])], ignore_index=True)
                responses_df.to_csv(RESPONSES_FILE, index=False)
                st.success("답안이 제출되었습니다!")
                
                # 즉시 채점 결과 표시
                if os.path.exists(ANSWERS_FILE):
                    answers_df = pd.read_csv(ANSWERS_FILE)
                    filtered_answers = answers_df[
                        (answers_df['회차'] == exam_round) & 
                        (answers_df['과목'] == subject)
                    ]
                    
                    correct_count = 0
                    for i, answer in enumerate(answers):
                        correct_answer = filtered_answers[
                            filtered_answers['문항번호'] == i+1
                        ]['정답'].iloc[0]
                        
                        if answer == correct_answer:
                            correct_count += 1
                    
                    st.subheader("채점 결과")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("맞은 개수", correct_count)
                    with col2:
                        st.metric("틀린 개수", num_questions - correct_count)
                    with col3:
                        st.metric("정답률", f"{(correct_count/num_questions)*100:.1f}%")
    elif authentication_status == False:
        st.error('아이디/비밀번호가 잘못되었습니다.')
    elif authentication_status == None:
        st.warning('아이디와 비밀번호를 입력하세요.')
except Exception as e:
    st.error(f'로그인 중 오류가 발생했습니다: {str(e)}')
    st.stop() 