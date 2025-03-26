import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
import streamlit_authenticator as stauth
from dotenv import load_dotenv
import yaml
from yaml.loader import SafeLoader
import bcrypt

# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="모의고사 자가채점 시스템",
    page_icon="📝",
    layout="wide"
)

# 데이터 디렉토리 생성
if not os.path.exists('data'):
    os.makedirs('data')

# 인증 설정
def load_config():
    if os.path.exists('config.yaml'):
        with open('config.yaml') as file:
            return yaml.load(file, Loader=SafeLoader)
    return {
        'credentials': {
            'usernames': {
                'admin': {
                    'email': 'admin@example.com',
                    'name': '관리자',
                    'password': 'admin123'
                }
            }
        },
        'cookie': {
            'expiry_days': 30,
            'key': 'yeonhap_test_key_123',
            'name': 'yeonhap_test_cookie'
        }
    }

config = load_config()

# 설정 파일 저장
def save_config():
    with open('config.yaml', 'w') as file:
        yaml.dump(config, file, allow_unicode=True)

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
    name, authentication_status, username = authenticator.login(fields=['username', 'password'])
    
    if authentication_status:
        st.success(f"환영합니다 {name}님!")
        
        # 사이드바
        authenticator.logout('로그아웃', 'sidebar')
        
        # 제목
        st.title(f"📝 모의고사 자가채점 시스템 - {name}님 환영합니다")
        
        # 데이터 파일 경로
        ANSWERS_FILE = "data/answers.csv"
        RESPONSES_FILE = "data/responses.csv"
        STUDENT_ANSWERS_FILE = "data/student_answers.csv"
        STUDENT_SUBJECTS_FILE = "data/student_subjects.csv"  # 학생별 과목 선택 파일 추가
        
        # 데이터 파일이 없으면 생성
        def initialize_data_files():
            if not os.path.exists(ANSWERS_FILE):
                pd.DataFrame({
                    '회차': [],
                    '과목': [],
                    '문항번호': [],
                    '정답': [],
                    '배점': []
                }).to_csv(ANSWERS_FILE, index=False)
            
            if not os.path.exists(RESPONSES_FILE):
                pd.DataFrame({
                    '학생ID': [],
                    '회차': [],
                    '과목': [],
                    '문항번호': [],
                    '입력답': []
                }).to_csv(RESPONSES_FILE, index=False)
            
            if not os.path.exists(STUDENT_ANSWERS_FILE):
                pd.DataFrame({
                    '학생ID': [],
                    '회차': [],
                    '과목': [],
                    '문항번호': [],
                    '정답': []
                }).to_csv(STUDENT_ANSWERS_FILE, index=False)
                
            if not os.path.exists(STUDENT_SUBJECTS_FILE):
                pd.DataFrame({
                    '학생ID': [],
                    '회차': [],
                    '탐구1': [],
                    '탐구2': []
                }).to_csv(STUDENT_SUBJECTS_FILE, index=False)
        
        initialize_data_files()
        
        # 메인 컨텐츠
        if username == 'admin':
            st.header("관리자 설정")
            
            # 탭 생성
            tab1, tab2 = st.tabs(["계정 관리", "시스템 설정"])
            
            with tab1:
                st.subheader("계정 추가")
                new_username = st.text_input("아이디")
                new_name = st.text_input("이름")
                new_email = st.text_input("이메일")
                new_password = st.text_input("비밀번호", type="password")
                account_type = st.selectbox("계정 유형", ["교사", "학생"])
                
                if st.button("계정 추가"):
                    if new_username and new_name and new_email and new_password:
                        if new_username not in config['credentials']['usernames']:
                            config['credentials']['usernames'][new_username] = {
                                'email': new_email,
                                'name': new_name,
                                'password': new_password
                            }
                            save_config()
                            st.success("계정이 추가되었습니다!")
                        else:
                            st.error("이미 존재하는 아이디입니다.")
                    else:
                        st.error("모든 필드를 입력해주세요.")
                
                st.subheader("계정 목록")
                accounts_df = pd.DataFrame([
                    {
                        '아이디': username,
                        '이름': info['name'],
                        '이메일': info['email']
                    }
                    for username, info in config['credentials']['usernames'].items()
                ])
                st.dataframe(accounts_df)
            
            with tab2:
                st.subheader("시스템 설정")
                st.write("추가 설정 옵션은 여기에 구현될 예정입니다.")
        
        elif username == 'teacher':
            st.header("교사용 관리")
            
            # 탭 생성
            tab1, tab2, tab3, tab4 = st.tabs(["정답 입력", "채점 결과", "통계 분석", "학생 정답 확인"])
            
            with tab1:
                # 정답 입력
                st.subheader("정답 입력")
                exam_round = st.selectbox("모의고사 회차를 선택하세요", ["1차", "2차", "3차", "4차"], key='teacher_round')
                subject = st.selectbox(
                    "과목을 선택하세요",
                    ["국어", "수학", "영어", "한국사", 
                     "물리학", "화학", "생명과학", "지구과학", 
                     "생활과 윤리", "윤리와 사상", "한국지리", "세계지리",
                     "동아시아사", "세계사", "경제", "정치와 법", "사회문화"],
                    key='teacher_subject'
                )
                
                # 과목별 문항 수 설정
                subject_questions = {
                    "국어": 45,
                    "수학": 30,
                    "영어": 45,
                    "한국사": 20,
                    "물리학": 20,
                    "화학": 20,
                    "생명과학": 20,
                    "지구과학": 20,
                    "생활과 윤리": 20,
                    "윤리와 사상": 20,
                    "한국지리": 20,
                    "세계지리": 20,
                    "동아시아사": 20,
                    "세계사": 20,
                    "경제": 20,
                    "정치와 법": 20,
                    "사회문화": 20
                }
                
                num_questions = subject_questions[subject]
                
                # 기존 정답 불러오기
                answers_df = pd.read_csv(ANSWERS_FILE)
                existing_answers = answers_df[
                    (answers_df['회차'] == exam_round) & 
                    (answers_df['과목'] == subject)
                ]
                
                # 기본 배점 설정
                default_point = st.number_input(
                    "기본 배점을 입력하세요 (소수점 첫째자리까지)",
                    min_value=0.0,
                    max_value=5.0,
                    value=2.0,
                    step=0.1,
                    format="%.1f"
                )
                
                # 정답 입력 폼
                with st.form("answer_form"):
                    st.write("문항별 정답과 배점을 입력하세요 (기본 배점과 다른 경우에만 수정)")
                    answers = {}
                    points = {}  # 배점 저장용 딕셔너리
                    
                    for i in range(1, num_questions + 1):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            # 기존 정답이 있으면 표시
                            existing_answer = ""
                            if not existing_answers.empty:
                                answer_row = existing_answers[existing_answers['문항번호'] == i]
                                if not answer_row.empty:
                                    existing_answer = str(int(answer_row['정답'].iloc[0]))  # 소수점 제거
                            answers[i] = st.text_input(f"{i}번", value=existing_answer)
                        with col2:
                            # 기존 배점이 있으면 표시, 없으면 기본 배점 사용
                            existing_point = default_point
                            if not existing_answers.empty:
                                point_row = existing_answers[existing_answers['문항번호'] == i]
                                if not point_row.empty:
                                    existing_point = point_row['배점'].iloc[0]
                            points[i] = st.number_input(
                                f"{i}번 배점",
                                min_value=0.0,
                                max_value=5.0,
                                value=float(existing_point),
                                step=0.1,
                                format="%.1f"
                            )
                    
                    submitted = st.form_submit_button("정답 저장")
                    
                    if submitted:
                        # 기존 정답 삭제
                        answers_df = answers_df[
                            ~((answers_df['회차'] == exam_round) & 
                              (answers_df['과목'] == subject))
                        ]
                        
                        # 새로운 정답 추가
                        for i in range(1, num_questions + 1):
                            new_row = {
                                '회차': exam_round,
                                '과목': subject,
                                '문항번호': i,
                                '정답': str(int(float(answers[i]))) if answers[i] else "",  # 소수점 제거
                                '배점': points[i]  # 배점 추가
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
                    
                    if not responses_df.empty and not answers_df.empty:
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
                        
                        if subject_stats:
                            subject_stats_df = pd.DataFrame(subject_stats)
                            
                            # 과목별 평균 정답률 시각화
                            fig = px.bar(subject_stats_df, x='과목', y='평균정답률',
                                        title='과목별 평균 정답률',
                                        labels={'과목': '과목', '평균정답률': '평균 정답률 (%)'})
                            st.plotly_chart(fig)
                        else:
                            st.info("아직 과목별 통계 데이터가 없습니다.")
                        
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
                        
                        if round_stats:
                            round_stats_df = pd.DataFrame(round_stats)
                            
                            # 회차별 추이 시각화
                            fig = px.line(round_stats_df, x='회차', y='평균정답률',
                                         title='회차별 평균 정답률 추이',
                                         labels={'회차': '회차', '평균정답률': '평균 정답률 (%)'})
                            st.plotly_chart(fig)
                        else:
                            st.info("아직 회차별 통계 데이터가 없습니다.")
                    else:
                        st.info("아직 답안이나 정답 데이터가 없습니다.")
                else:
                    st.info("아직 답안 데이터가 없습니다.")
            
            with tab4:
                # 학생 정답 확인
                st.subheader("학생 정답 확인")
                if os.path.exists(STUDENT_ANSWERS_FILE):
                    student_answers_df = pd.read_csv(STUDENT_ANSWERS_FILE)
                    if not student_answers_df.empty:
                        selected_round = st.selectbox("확인할 회차를 선택하세요", student_answers_df['회차'].unique(), key='teacher_check_round')
                        selected_subject = st.selectbox("확인할 과목을 선택하세요", student_answers_df['과목'].unique(), key='teacher_check_subject')
                        
                        filtered_student_answers = student_answers_df[
                            (student_answers_df['회차'] == selected_round) & 
                            (student_answers_df['과목'] == selected_subject)
                        ]
                        
                        if not filtered_student_answers.empty:
                            st.dataframe(filtered_student_answers)
                        else:
                            st.info("해당 회차/과목에 대한 학생 정답이 없습니다.")
                    else:
                        st.info("학생이 입력한 정답이 없습니다.")
                else:
                    st.info("학생 정답 파일이 없습니다.")
        else:
            st.header("학생용 자가채점")
            
            # 탐구 과목 선택
            st.subheader("탐구 과목 선택")
            exam_round = st.selectbox("모의고사 회차를 선택하세요", ["1차", "2차", "3차", "4차"], key='subject_round')
            
            # 기존 선택 과목 불러오기
            subjects_df = pd.read_csv(STUDENT_SUBJECTS_FILE)
            selected_subjects = subjects_df[
                (subjects_df['학생ID'] == username) & 
                (subjects_df['회차'] == exam_round)
            ]
            
            # 탐구 과목 목록
            science_subjects = ["물리학", "화학", "생명과학", "지구과학"]
            social_subjects = ["생활과 윤리", "윤리와 사상", "한국지리", "세계지리",
                             "동아시아사", "세계사", "경제", "정치와 법", "사회문화"]
            
            # 기본값 설정
            default_subject1 = selected_subjects['탐구1'].iloc[0] if not selected_subjects.empty else None
            default_subject2 = selected_subjects['탐구2'].iloc[0] if not selected_subjects.empty else None
            
            # 탐구 과목 선택 폼
            with st.form("subject_selection_form"):
                col1, col2 = st.columns(2)
                with col1:
                    subject1 = st.selectbox("탐구1 과목을 선택하세요", 
                                          science_subjects + social_subjects,
                                          index=(science_subjects + social_subjects).index(default_subject1) if default_subject1 else 0)
                with col2:
                    remaining_subjects = [s for s in science_subjects + social_subjects if s != subject1]
                    subject2 = st.selectbox("탐구2 과목을 선택하세요", 
                                          remaining_subjects,
                                          index=remaining_subjects.index(default_subject2) if default_subject2 in remaining_subjects else 0)
                
                submitted = st.form_submit_button("탐구 과목 저장")
                
                if submitted:
                    # 기존 선택 삭제
                    subjects_df = subjects_df[
                        ~((subjects_df['학생ID'] == username) & 
                          (subjects_df['회차'] == exam_round))
                    ]
                    
                    # 새로운 선택 추가
                    new_row = {
                        '학생ID': username,
                        '회차': exam_round,
                        '탐구1': subject1,
                        '탐구2': subject2
                    }
                    subjects_df = pd.concat([subjects_df, pd.DataFrame([new_row])], ignore_index=True)
                    subjects_df.to_csv(STUDENT_SUBJECTS_FILE, index=False)
                    st.success("탐구 과목이 저장되었습니다!")
            
            # 탭 생성
            tab1, = st.tabs(["답안 입력"])  # 정답 입력 탭 제거
            
            with tab1:
                # 답안 입력
                st.subheader("답안 입력")
                exam_round = st.selectbox("모의고사 회차를 선택하세요", ["1차", "2차", "3차", "4차"], key='student_round')
                
                # 학생의 탐구 과목 선택 확인
                subjects_df = pd.read_csv(STUDENT_SUBJECTS_FILE)
                student_subjects = subjects_df[
                    (subjects_df['학생ID'] == username) & 
                    (subjects_df['회차'] == exam_round)
                ]
                
                if student_subjects.empty:
                    st.warning("먼저 탐구 과목을 선택해주세요!")
                    st.stop()
                
                # 과목 선택 (탐구 과목은 미리 선택된 것만 표시)
                available_subjects = ["국어", "수학", "영어", "한국사"]
                if not student_subjects.empty:
                    available_subjects.extend([student_subjects['탐구1'].iloc[0], student_subjects['탐구2'].iloc[0]])
                
                subject = st.selectbox(
                    "과목을 선택하세요",
                    available_subjects,
                    key='student_subject'
                )
                
                # 과목별 문항 수 설정
                subject_questions = {
                    "국어": 45,
                    "수학": 30,
                    "영어": 45,
                    "한국사": 20,
                    "물리학": 20,
                    "화학": 20,
                    "생명과학": 20,
                    "지구과학": 20,
                    "생활과 윤리": 20,
                    "윤리와 사상": 20,
                    "한국지리": 20,
                    "세계지리": 20,
                    "동아시아사": 20,
                    "세계사": 20,
                    "경제": 20,
                    "정치와 법": 20,
                    "사회문화": 20
                }
                
                num_questions = subject_questions[subject]
                
                # 답안 입력 폼
                with st.form("student_answer_form"):
                    answers = []
                    for i in range(num_questions):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"{i+1}번")
                        with col2:
                            answer = st.text_input(f"답", key=f"student_q_{i}")
                            answers.append(answer if answer else "")  # 빈 값 처리
                    
                    submitted = st.form_submit_button("답안 제출")
                    
                    if submitted:
                        # 기존 답안 삭제
                        responses_df = pd.read_csv(RESPONSES_FILE)
                        responses_df = responses_df[
                            ~((responses_df['학생ID'] == username) & 
                              (responses_df['회차'] == exam_round) & 
                              (responses_df['과목'] == subject))
                        ]
                        
                        # 새 답안 추가
                        for i, answer in enumerate(answers):
                            if answer:  # 답안이 있는 경우만 저장
                                new_row = {
                                    '학생ID': username,
                                    '회차': exam_round,
                                    '과목': subject,
                                    '문항번호': i+1,
                                    '입력답': answer
                                }
                                responses_df = pd.concat([responses_df, pd.DataFrame([new_row])], ignore_index=True)
                        responses_df.to_csv(RESPONSES_FILE, index=False)
                        st.success("답안이 저장되었습니다!")
                        
                        # 즉시 채점 결과 표시
                        if os.path.exists(ANSWERS_FILE):
                            answers_df = pd.read_csv(ANSWERS_FILE)
                            filtered_answers = answers_df[
                                (answers_df['회차'] == exam_round) & 
                                (answers_df['과목'] == subject)
                            ]
                            
                            if not filtered_answers.empty:
                                correct_count = 0
                                total_answered = 0  # 실제로 답한 문항 수
                                for i, answer in enumerate(answers):
                                    if answer:  # 답안이 있는 경우만 채점
                                        total_answered += 1
                                        correct_answer = filtered_answers[
                                            filtered_answers['문항번호'] == i+1
                                        ]['정답'].iloc[0]
                                        
                                        # 정답과 입력답을 문자열로 변환하고 공백 제거
                                        answer_str = str(answer).strip()
                                        correct_answer_str = str(correct_answer).strip()
                                        
                                        # 디버깅을 위한 출력
                                        st.write(f"문항 {i+1}: 입력답={answer_str}, 정답={correct_answer_str}")
                                        
                                        if answer_str == correct_answer_str:
                                            correct_count += 1
                                
                                if total_answered > 0:  # 답안을 하나라도 입력한 경우에만 결과 표시
                                    st.subheader("채점 결과")
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("맞은 개수", correct_count)
                                    with col2:
                                        st.metric("틀린 개수", total_answered - correct_count)
                                    with col3:
                                        st.metric("정답률", f"{(correct_count/total_answered)*100:.1f}%")
                                else:
                                    st.warning("답안을 입력해주세요.")
                            else:
                                st.warning("해당 회차/과목의 정답이 아직 등록되지 않았습니다.")
    elif authentication_status == False:
        st.error('아이디/비밀번호가 잘못되었습니다.')
    elif authentication_status == None:
        st.warning('아이디와 비밀번호를 입력하세요.')
except Exception as e:
    st.error(f'로그인 중 오류가 발생했습니다: {str(e)}')
    st.stop() 