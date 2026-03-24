// src/services/dataService.js
import axios from 'axios';

// 원격 데이터 URL (GitHub Raw 콘텐츠 주소)
const REMOTE_DATA_URL = 'https://raw.githubusercontent.com/kyunghokim1895/app01/main/HKTVGlobalApp/src/services/data.json';

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
                title: '미국 증시 마감 리뷰 (샘플)',
                summary: '한국경제TV 글로벌 채널의 미국 증시 분석 샘플 데이터입니다.',
                summaryList: [
                    '1. 샘플 데이터입니다. 실제 데이터가 로드되면 자동으로 교체됩니다.'
                ],
                keywords: ['#미국증시', '#글로벌', '#투자', '#샘플'],
                publishedAt: '2026-03-24',
                videoUrl: 'https://youtube.com/watch?v=example1'
            }
        ];
    }
};
