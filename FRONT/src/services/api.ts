const API_BASE_URL = 'http://localhost:8000';

export interface AnalysisResponse {
  id: string;
}

export interface SSEEvent {
  type: string;
  payload: any;
}

export class AnalysisService {
  static async beginAnalysis(repoUrl: string): Promise<AnalysisResponse> {
    const formData = new URLSearchParams();
    formData.append('repo', repoUrl);

    const response = await fetch(`${API_BASE_URL}/begin-analysis`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Failed to start analysis: ${response.statusText}`);
    }

    return response.json();
  }

  static subscribeToAnalysis(
    pipelineId: string,
    onEvent: (event: SSEEvent) => void,
    onError?: (error: Error) => void
  ): EventSource {
    const eventSource = new EventSource(`${API_BASE_URL}/analysis/${pipelineId}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('SSE Event received:', data);
        onEvent(data);
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
        if (onError) onError(err as Error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      if (onError) onError(new Error('SSE connection failed'));
    };

    return eventSource;
  }
}