company1 = {
    'company_form': {
        'name': '有一个公司',
        'contact': '连喜仁',
        'phone': '13712345678',
        'email': 'xasdf@yahoo.com',
        'address': '北京！北京！',
        'contract_upload_result': '94017386-6fac-11e9-a419-acbc329114cf.r.pdf',
    },
    'projects': [
        {'name': '项目1'},
        {'name': '项目2'},
        {'name': '项目3'},
    ],
    'purchases': [
        {'pre_username': 'cg1', 'real_name': '蔡勾1', 'gender': 1, 'phone': '13700000001', 'email': '1adasdf@yahoo.com'},
        {'pre_username': 'cg2', 'real_name': '蔡勾2', 'gender': 0, 'phone': '13700000002', 'email': '1dasdf@yahoo.com'},
    ],
    'pms': [
        {'pre_username': 'pm1', 'real_name': '项经', 'gender': 1, 'phone': '13700000003', 'email': '1asadf@yahoo.com'},
        {'pre_username': 'pm2', 'real_name': '项理', 'gender': 0, 'phone': '13700000004', 'email': '1aadsdf@yahoo.com'},
        {'pre_username': 'pm3', 'real_name': '向经', 'gender': 1, 'phone': '13700000005', 'email': '1aadfsdf@yahoo.com'},
    ],
    'positions': [
        {'name': 'python工程师'}, {'name': 'java工程师'}, {'name': 'c#工程师'}, {'name': '前端'},
    ],
    'position_levels': [
        {'name': 'p1'}, {'name': 'p2'}, {'name': 'p3'}, {'name': 'p4'}, {'name': 'p5'}, {'name': 'p6'},
    ],
    'projects': [
        {'name': '项目1'},
        {'name': '项目2'},
        {'name': '项目3'},
        {'name': '项目4'},
        {'name': '项目5'},
    ],
    'offers': {
        'name': lambda x: '需求_{}'.format(x),
        'position_level_id': lambda position_level_len: position_level_len % 6,
        'position_id': lambda position_len: position_len % 4,
        'amount': lambda x: 3 + x % 5,
        'description': '一个需求',
    },
}

engineers = {'pre_username': lambda x: 'e{}'.format(x),
             'real_name': lambda x: '赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨'[x % 16] + str(x),
             'gender': lambda x: [0, 1][x % 2],
             'phone': lambda x: '137000{}'.format(10000 + x),
             'email': lambda x: 'e{}@qq.com'.format(x),
             'highest_degree': lambda x: '本科',
             "major": lambda x: "专业",
             'educations': lambda x: [{"school": "清华", "major": "拖拉机", "degree": "本科", "start_date": "2011-01-01", "end_date": "2014-01-01"}],
             'abilities': lambda x: [{"name": "python", "level": "3年"}, {"name": "java", "level": "2年"}],
             "welfare_rate": lambda x: 2000,
             "pay_welfare": lambda x: True
             }
