// src/services/dataService.js
import axios from 'axios';

// 원격 데이터 URL (GitHub Raw 콘텐츠 주소)
const REMOTE_DATA_URL = 'https://raw.githubusercontent.com/kyunghokim1895/app01/main/SentvSummaryApp/src/services/data.json';

export const fetchSummaries = async () => {
    try {
        // 1. 원격지에서 최신 데이터 가져오기 시도 (캐시 방지 파라미터 추가)
        console.log('Fetching remote data...');
        const timestamp = new Date().getTime();
        const response = await axios.get(`${REMOTE_DATA_URL}?t=${timestamp}`, { timeout: 10000 });
        if (response.data && Array.isArray(response.data)) {
            console.log('Successfully loaded remote data');
            return response.data;
        }
    } catch (remoteError) {
        console.log('Remote data fetch failed, trying local data:', remoteError.message);
    }

    try {
        // 2. 원격 실패 시 앱에 내장된 실제 데이터 가져오기 시도
        const realData = require('./data.json');
        return realData;
    } catch (error) {
        console.log('Real data not found, using mock data');
        // 3. 데이터가 모두 없으면 샘플 데이터 반환
        return [
            {
                id: '1',
                title: '삼성전자 실적 발표, 반도체 부활의 신호탄인가? (샘플)',
                summary: '2024년 2분기 삼성전자 실적 분석입니다. 반도체 부문의 이익 개선세가 뚜렷하며, HBM 공급 확대가 향후 주가의 핵심 변수가 될 전망입니다.',
                summaryList: [
                    '1. 2024년 2분기 삼성전자 반도체 부문이 흑자 전환에 성공하며 실적 반등을 이끌었습니다.',
                    '2. 특히 AI 시장 확대에 따른 HBM3E 및 DDR5 등 고부가 가치 메모리 수요가 급증했습니다.',
                    '3. 파운드리 부문에서도 수주 확대를 통해 하반기 수익성 개선이 기대되는 상황입니다.',
                    '4. 증권가에서는 삼성전자의 기술 경쟁력 회복을 긍정적으로 평가하며 목표 주가를 상향하고 있습니다.',
                    '5. 향후 거시 경제 변수 속에서도 반도체 업턴 사이클 진입은 확고해 보인다는 분석입니다.'
                ],
                keywords: ['#삼성전자', '#반도체', '#실적발표', '#주식'],
                publishedAt: '2024-02-18',
                videoUrl: 'https://youtube.com/watch?v=example1'
            }
        ];
    }
};
