# Add this function to clipper/views.py after the cancel_processing function

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_video_processing(request, video_request_id):
    """Cancel processing for a video request"""
    from core.models import ProcessingQueue, VideoRequest
    from core.queue_manager import QueueManager

    try:
        # Get the video request
        video_request = VideoRequest.objects.get(
            id=video_request_id,
            user=request.user
        )

        # Find the associated queue entry
        queue_entry = ProcessingQueue.objects.filter(
            video_request=video_request,
            status__in=['queued', 'processing']
        ).first()

        if not queue_entry:
            return Response({
                'error': 'No active processing found for this video request'
            }, status=status.HTTP_404_NOT_FOUND)

        # Cancel the task
        success = QueueManager.cancel_task(queue_entry)

        if success:
            # Also update video request status
            video_request.status = 'cancelled'
            video_request.save()

            return Response({
                'message': f'Video processing cancelled successfully',
                'video_request_id': video_request_id,
                'status': 'cancelled'
            })
        else:
            return Response({
                'error': 'Cannot cancel processing - it may be too late to stop'
            }, status=status.HTTP_400_BAD_REQUEST)

    except VideoRequest.DoesNotExist:
        return Response({
            'error': 'Video request not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': f'Error cancelling processing: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)