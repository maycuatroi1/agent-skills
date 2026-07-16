import type { ContentModule } from 'omelet-slide-generator';

const content: ContentModule = {
  courseLabel: 'Course Label',
  meta: {
    title: 'Lecture Title',
    author: 'Your Name',
    subject: 'Lecture 1',
  },
  slides: [
    {
      layout: 'title',
      title: 'Lecture Title',
      subtitle: 'Subtitle goes here',
      author: 'Your Name',
      date: 'YYYY-MM-DD',
    },
    {
      layout: 'objectives',
      title: 'Today',
      items: [
        'First objective',
        'Second objective',
        'Third objective',
      ],
    },
    {
      layout: 'agenda',
      title: 'Agenda',
      items: [
        { time: '00:00', label: 'Intro',  type: 'lecture' },
        { time: '00:20', label: 'Topic A', type: 'lecture' },
        { time: '00:50', label: 'Lab',     type: 'lab' },
        { time: '01:30', label: 'Q&A',     type: 'discussion' },
      ],
    },
    {
      layout: 'bullets',
      title: 'Key ideas',
      items: [
        'First idea',
        'Second idea',
        'Third idea',
      ],
      notes: 'Speaker notes for this slide.',
    },
    {
      layout: 'codeBlock',
      title: 'Example',
      language: 'ts',
      code: `function hello(name: string): string {
  return \`Hello, \${name}!\`;
}`,
    },
    {
      layout: 'summary',
      title: 'Recap',
      items: [
        'Recap point 1',
        'Recap point 2',
        'Recap point 3',
      ],
    },
    { layout: 'qna', title: 'Questions?' },
  ],
};

export default content;
